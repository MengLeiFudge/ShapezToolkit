"""先建立无反馈组合步，再以同一四阶段时钟闭合全部主副寄存器。"""

from dataclasses import replace

from .circuit import Gate, Literal, Ref
from .corner_program import CornerProgram
from .sequential_circuit import Clock, clock


class ClockedState:
    """put按调用顺序覆盖；后写条件优先，所有状态在同一周期同时更新。"""

    def __init__(self, program: CornerProgram):
        self.program = program
        self.initial: dict[Ref, Ref | Literal] = {}
        self.next: dict[Ref, Ref] = {}
        self.closed = False

    def add(self, value: int | None | Ref = 0) -> Ref:
        """建立读占位；目标相关初值必须在完整复位期间保持。"""
        if self.closed:
            raise ValueError("主副寄存器已闭合，不能再增加状态")
        initial = value if isinstance(value, Ref) else Literal(value)
        read = self.program.circuit.add("LogicGateIf", initial, Literal(1))
        self.initial[read] = initial
        self.next[read] = read
        return read

    def put(self, read: Ref, value: Ref | int | None, condition: Ref | None = None) -> None:
        """条件写入一项next；不改变本周期读取的旧状态。"""
        if self.closed or read not in self.next:
            raise ValueError("只能更新尚未闭合的本组寄存器")
        source = value if isinstance(value, Ref) else self.program.const(value)
        self.next[read] = source if condition is None else self.program.pick(condition, source, self.next[read])

    def put_exclusive(self, read: Ref, choices: tuple[tuple[Ref, Ref | int | None], ...]) -> None:
        """调用者证明条件互斥；并行选择写值，未选中时保留此前next。"""
        if self.closed or read not in self.next or not choices:
            raise ValueError("并行条件写入需要本组未闭合寄存器及至少一项选择")
        circuit = self.program.circuit
        branches = tuple(circuit.add("LogicGateIf", value if isinstance(value, Ref) else Literal(value), condition)
                         for condition, value in choices)
        keep = self.program.not_(self.program.or_(*(condition for condition, _ in choices)))
        retained = circuit.add("LogicGateIf", self.next[read], keep)
        circuit.aliases.append((*branches, retained))
        self.next[read] = branches[0]


    def close(self, enable: Ref, *, slow_reads: tuple[Ref, ...] = (), slow_event: Ref | None = None,
              pulses: tuple[Ref, ...] = (), local_pairs: bool = False) -> tuple[Clock, dict]:
        """慢根更新后冻结一轮，脉冲在冻结期清零；分别核对3P/7P传播窗。"""
        if self.closed:
            raise ValueError("同一组主副寄存器只能闭合一次")
        if bool(slow_reads) != (slow_event is not None) or (pulses and not slow_reads):
            raise ValueError("慢状态与更新事件必须成对提供，脉冲需要慢状态协议")
        if len(set(slow_reads)) != len(slow_reads) or len(set(pulses)) != len(pulses) or any(
                read not in self.initial for read in (*slow_reads, *pulses)) or set(slow_reads) & set(pulses):
            raise ValueError("慢状态及脉冲必须来自本组，互不重复且互不重叠")
        circuit = self.program.circuit
        if slow_event is not None:
            reads = tuple(self.initial)
            cooling = self.add()
            ready = self.program.not_(cooling)
            self.put(cooling, self.program.and_(ready, slow_event))
            for read in reads:
                self.next[read] = (self.program.and_(ready, self.next[read]) if read in pulses else
                                   self.program.pick(ready, self.next[read], read))
        if local_pairs:
            circuit.local_nodes.update(set(range(len(circuit.gates))) - {read.node for read in self.initial})
        full_depth = circuit.settling_bound()["max_gate_depth"]
        all_reads = tuple(self.initial)
        fast_reads = tuple(read for read in all_reads if read not in slow_reads)
        fast_path: list[Ref] = []
        depth = circuit.changing_depth(fast_reads, trace=fast_path)
        path_nodes = [{"node": reference.node, "port": reference.port, "kind": circuit.gates[reference.node].kind}
                      for reference in fast_path]
        slow_path: list[Ref] = []
        slow_depth = circuit.changing_depth(slow_reads, trace=slow_path) if slow_reads else 0
        slow_nodes = [{"node": reference.node, "port": reference.port, "kind": circuit.gates[reference.node].kind}
                      for reference in slow_path]
        phase_steps = max(8, (depth + 7) // 3, (slow_depth + 10) // 7)
        timing = clock(circuit, enable, phase_steps=phase_steps)
        timing = replace(timing, reset_ticks=max(timing.reset_ticks, 12 * full_depth + 256))
        reset = self.program.not_(enable)
        master_load = self.program.or_(timing.phases[0], reset)
        slave_load = self.program.or_(timing.phases[2], reset)
        for read, initial in self.initial.items():
            data = self.program.control(enable).select(self.next[read], initial)
            master = self.program.control(master_load).latch(data)
            slave_data = self.program.control(enable).select(master, initial)
            slave = self.program.control(slave_load).latch(slave_data)
            circuit.gates[read.node] = Gate("LogicGateIf", (slave, Literal(1)))
        self.closed = True
        report = {"state_registers": len(self.initial), "step_max_gate_depth": depth,
                  "initial_max_gate_depth": full_depth,
                  "step_critical_path": path_nodes}
        if slow_reads:
            report.update({"slow_max_gate_depth": slow_depth, "slow_handoff_phases": 7,
                           "slow_update_wait_cycles": 1, "slow_state_registers": len(slow_reads),
                           "slow_critical_path": slow_nodes})
        return timing, report
