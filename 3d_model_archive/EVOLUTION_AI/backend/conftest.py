import sys
from pathlib import Path

# 确保 backend 根目录在 sys.path 中
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
