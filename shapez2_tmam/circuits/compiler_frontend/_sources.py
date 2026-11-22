"""读取编译涉及的 Python 源码，定位顶层方法和显式相对导入。"""

import ast
import tokenize
from dataclasses import dataclass
from pathlib import Path


class FrontendError(SyntaxError):
    """带文件、行列和源码的前端诊断。"""


@dataclass(frozen=True)
class _Binding:
    node: ast.stmt
    alias: ast.alias | None = None


class _Source:
    def __init__(self, source: str, filename: str, path: Path | None):
        self.filename = filename
        self.path = path
        self.lines = source.splitlines()
        try:
            tree = ast.parse(source, filename)
        except SyntaxError as error:
            raise FrontendError(error.msg, (filename, error.lineno, error.offset, error.text)) from error
        self.bindings: dict[str, list[_Binding]] = {}
        self.body = tree.body
        for node in self.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.bindings.setdefault(node.name, []).append(_Binding(node))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    self.bindings.setdefault(name, []).append(_Binding(node, alias))
            elif isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign) and node.value is not None:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for child in ast.walk(target):
                        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                            self.bindings.setdefault(child.id, []).append(_Binding(node))

    def error(self, node: ast.AST | None, message: str) -> FrontendError:
        line = getattr(node, "lineno", 1)
        text = self.lines[line - 1] if line <= len(self.lines) else ""
        offset = len(text.encode()[:getattr(node, "col_offset", 0)].decode()) + 1
        return FrontendError(message, (self.filename, line, offset, text))

    def binding(self, name: str) -> _Binding | None:
        found = self.bindings.get(name, [])
        if len(found) > 1:
            raise self.error(found[1].node, f"“{name}”有同名的顶层定义或导入，请保留一个或为导入指定别名")
        return found[0] if found else None

    def literal_table(self, use: ast.Name) -> ast.Tuple:
        name = use.id
        binding = self.binding(name)
        if binding is None:
            raise self.error(use, f"找不到只读表“{name}”，请在同文件顶层定义字面量元组")
        node = binding.node
        if (not isinstance(node, ast.Assign) or len(node.targets) != 1
                or not isinstance(node.targets[0], ast.Name) or not isinstance(node.value, ast.Tuple)):
            raise self.error(node, f"只读表“{name}”须用一个顶层赋值直接绑定字面量元组")

        pending: list[ast.AST] = [stmt for stmt in self.body if stmt is not node]
        while pending:
            child = pending.pop()
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                rebinds = child.name == name
                pending.extend(part for part in ast.iter_child_nodes(child) if not isinstance(part, ast.stmt))
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                rebinds = any((alias.asname or alias.name.split(".")[0]) == name for alias in child.names)
            elif isinstance(child, ast.Lambda):
                rebinds = False
                pending.append(child.args)
            elif isinstance(child, ast.comprehension):
                rebinds = False
                pending.extend((child.iter, *child.ifs))
            else:
                if isinstance(child, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
                    rebinds = child.name == name
                elif isinstance(child, ast.MatchMapping):
                    rebinds = child.rest == name
                else:
                    rebinds = (isinstance(child, ast.Name) and child.id == name
                               and isinstance(child.ctx, (ast.Store, ast.Del)))
                pending.extend(ast.iter_child_nodes(child))
            if rebinds:
                raise self.error(child, f"顶层只读表“{name}”只允许定义一次")
        return node.value


@dataclass(frozen=True)
class _Method:
    source: _Source
    node: ast.FunctionDef


class _Sources:
    def __init__(self, source: str, filename: str):
        path = None if filename.startswith("<") and filename.endswith(">") else Path(filename).resolve()
        self.root = _Source(source, filename, path)
        self.loaded = {path: self.root} if path is not None else {}

    def name(self, method: _Method) -> str:
        if method.source is self.root:
            return method.node.name
        assert method.source.path is not None and self.root.path is not None
        path = method.source.path.relative_to(self.root.path.parent).with_suffix("")
        return ".".join((*path.parts, method.node.name))

    def method(self, source: _Source, name: str, location: ast.AST) -> _Method:
        requester, use = source, location
        chain: list[tuple[_Source, str]] = []
        while (source, name) not in chain:
            chain.append((source, name))
            binding = source.binding(name)
            if binding is None:
                raise requester.error(use, f"在 {source.filename} 找不到顶层方法“{name}”")
            node = binding.node
            if isinstance(node, ast.FunctionDef):
                return _Method(source, node)
            if not isinstance(node, ast.ImportFrom) or node.level != 1 or binding.alias is None:
                raise source.error(node, f"“{name}”需要顶层纯方法或 `from .模块 import 方法` 导入")
            requester, use = source, binding.alias
            source = self.load(source, node)
            name = binding.alias.name
        cycle = " → ".join(f"{owner.filename} 中的 {symbol}" for owner, symbol in (*chain, (source, name)))
        raise requester.error(use, f"相对导入形成循环（{cycle}）")

    def load(self, origin: _Source, node: ast.ImportFrom) -> _Source:
        if origin.path is None:
            raise origin.error(node, "相对导入需要 filename 指明当前 Python 源码的路径")
        directory = origin.path.parent
        if node.module is None:
            candidates = (directory / "__init__.py",)
        else:
            base = directory.joinpath(*node.module.split("."))
            candidates = (base / "__init__.py", base.with_suffix(".py"))
        candidate = next((path for path in candidates if path.is_file()), candidates[-1])
        path = candidate.resolve()
        if not path.is_relative_to(directory):
            raise origin.error(node, f"相对导入的源码须位于当前包目录（{candidate}）")
        if path in self.loaded:
            return self.loaded[path]
        try:
            with tokenize.open(path) as file:
                text = file.read()
        except FileNotFoundError as error:
            raise origin.error(node, f"找不到相对导入的源码文件 {candidate}") from error
        except (OSError, SyntaxError, UnicodeError) as error:
            raise origin.error(node, f"无法读取相对导入的源码文件 {candidate}（{error}）") from error
        source = _Source(text, str(candidate), path)
        self.loaded[path] = source
        return source
