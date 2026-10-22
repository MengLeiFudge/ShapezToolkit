"""ShapezToolkit 本机路径设置，由统一命令入口读取。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEAM_GAME_DIR = Path(r"D:\Steam\steamapps\common\shapez.io")
TOKEN_FILE = ROOT / "shapez1_puzzles" / ".local" / "shapez1-token.json"
PUZZLE_DIR = ROOT / "shapez1_puzzles" / "data"
MOD_DIR = ROOT / "shapez1_mods" / "data"
