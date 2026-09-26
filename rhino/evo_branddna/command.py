# -*- coding: utf-8 -*-
"""
EVO_BrandDNA 命令
=================

职责：
  1. 弹出品牌选择面板
  2. 取知识库车型参数 → 控制线几何
  3. 创建图层并写入当前 Rhino 文档（单条撤销记录）
  4. 尝试以 Rhino.Commands.Command 子类形式注册持久命令

命令注册说明：RhinoCode 支持脚本定义 Command 子类，注册成功后可在
命令行直接输入 EVO_BrandDNA；若当前版本不支持，则通过加载器
（load_evo.py）执行，行为等价。注册结果会在命令行明确提示。
"""
from __future__ import annotations

import Rhino

import brand_knowledge
from . import builder
from . import panel

COMMAND_NAME = "EVO_BrandDNA"

# 保持命令实例的全局引用，避免被垃圾回收
_command_instances = []


# ============================================================
# 核心流程
# ============================================================

def generate(doc, brand_key: str, model_key: str, scale: float = 1.0) -> int:
    """生成指定车型的控制线并写入文档，返回写入对象数"""
    model = brand_knowledge.get_model(brand_key, model_key)
    if model is None:
        Rhino.RhinoApp.WriteLine(f"[EVO] 车型不存在: {brand_key}/{model_key}")
        return 0

    layout = builder.compute_layout(model["params"], scale)
    geometry = builder.build_geometry(layout)
    geometry["labels"].append(builder.build_label(model, layout))

    # 确保图层存在 → 键到图层索引
    layer_index = {}
    for key, (name, rgb) in builder.LAYERS.items():
        layer = doc.Layers.FindName(name)
        if layer is None:
            import System
            layer = Rhino.DocObjects.Layer()
            layer.Name = name
            layer.Color = System.Drawing.Color.FromArgb(rgb[0], rgb[1], rgb[2])
            idx = doc.Layers.Add(layer)
            layer_index[key] = idx
        else:
            layer_index[key] = layer.Index

    # 单条撤销记录内写入全部对象
    undo = doc.BeginUndoRecord("EVO 品牌造型 DNA")
    count = 0
    try:
        for key, geos in geometry.items():
            attr = Rhino.DocObjects.ObjectAttributes()
            attr.LayerIndex = layer_index[key]
            for geo in geos:
                if not geo.IsValid:
                    continue
                if doc.Objects.Add(geo, attr) != System_Guid_Empty():
                    count += 1
    finally:
        doc.EndUndoRecord(undo)

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        f"[EVO] {model['brand_zh_name']} {model['zh_name']} "
        f"×{scale:.2f}：已生成 {count} 个控制线对象")
    return count


def System_Guid_Empty():
    """System.Guid.Empty（doc.Objects.Add 失败返回值）"""
    import System
    return System.Guid.Empty


def run_interactive():
    """打开面板 → 生成（命令交互入口）"""
    doc = Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        Rhino.RhinoApp.WriteLine("[EVO] 当前没有打开的文档")
        return

    selection = panel.show_panel()
    if selection is None:
        Rhino.RhinoApp.WriteLine("[EVO] 已取消")
        return
    brand_key, model_key, scale = selection
    generate(doc, brand_key, model_key, scale)


def write_loaded_message():
    Rhino.RhinoApp.WriteLine(
        "[EVO] 品牌造型 DNA 已加载，运行命令: " + COMMAND_NAME)


# ============================================================
# 持久命令注册（实证支持；不支持时静默降级）
# ============================================================

try:
    from Rhino.Commands import Command as _Command, Result as _Result

    class EvoBrandDNACommand(_Command):
        def __init__(self):
            super(EvoBrandDNACommand, self).__init__()

        @property
        def EnglishName(self):
            return COMMAND_NAME

        def RunCommand(self, doc, mode):
            run_interactive()
            return _Result.Success

    def register_command():
        """实例化命令子类；RhinoCode 会自动发现并注册"""
        try:
            inst = EvoBrandDNACommand()
            _command_instances.append(inst)
            # 主动查询命令是否已注册，给出明确反馈
            cmd_id = Rhino.Commands.Command.Id(COMMAND_NAME)
            import System
            if cmd_id != System.Guid.Empty:
                Rhino.RhinoApp.WriteLine(f"[EVO] 命令已注册: {COMMAND_NAME}")
                return True
        except Exception as exc:  # noqa: BLE001
            Rhino.RhinoApp.WriteLine(f"[EVO] 命令注册未生效: {exc}")
        Rhino.RhinoApp.WriteLine(
            "[EVO] 请通过 RunPythonScript 运行 rhino/load_evo.py 打开面板")
        return False

except Exception:  # noqa: BLE001  # 非 Rhino 环境导入时
    def register_command():
        return False
