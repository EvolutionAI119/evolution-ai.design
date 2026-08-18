"""
pytest 配置 - 确保正确导入路径

将项目根目录（algorithm_model 的父目录）加入 sys.path，
使 algorithm_model 可作为顶层包被导入，
car_modeling 等子包的相对导入（from ..freeform）才能正常工作。
"""
import sys
import os

# 添加项目根目录到 path（algorithm_model 的父目录）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
