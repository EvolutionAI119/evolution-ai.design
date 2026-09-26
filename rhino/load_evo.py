#! python3
# ============================================================
# EVOLUTION-AI 品牌造型 DNA —— Rhino 插件加载器
# ============================================================
# 用法（任选其一）：
#   1. Rhino 命令：_RunPythonScript → 选择本文件
#   2. rhinocode CLI：rhinocode script load_evo.py
#   3. Script Editor 中打开本文件运行
#
# 本加载器做两件事：
#   a) 配置 sys.path：插件包目录 + backend/app（brand_knowledge.py 为纯
#      标准库模块，可直接在 RhinoCode CPython 3.9 运行，零改造复用）
#   b) 注册 EVO_BrandDNA 命令；若当前环境不支持脚本注册持久命令，
#      则直接打开品牌选择面板（等价于执行一次命令）
# ============================================================
import sys
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent                 # rhino/
_BACKEND_APP = _HERE.parent / "backend" / "app"                 # backend/app

for _p in (str(_HERE), str(_BACKEND_APP)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 首次加载打开面板；重复加载只注册命令（便于重复测试）
_IS_FIRST_LOAD = "evo_branddna" not in sys.modules

import evo_branddna.command as evo_command  # noqa: E402

# 尝试注册持久命令（成功后可直接在命令行输入 EVO_BrandDNA）
evo_command.register_command()

if __name__ == "__main__":
    if _IS_FIRST_LOAD:
        # 直接执行命令逻辑：弹出品牌选择面板
        evo_command.run_interactive()
    else:
        evo_command.write_loaded_message()
