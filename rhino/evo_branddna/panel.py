# -*- coding: utf-8 -*-
"""
品牌选择面板（Eto.Forms）
=========================

下拉选择：品牌（5）→ 车型（共 19）+ 放缩系数（0.50~1.50），
确认后返回 (brand_key, model_key, scale)；取消返回 None。
"""
from __future__ import annotations

import Eto.Forms as forms
import Eto.Drawing as drawing

import brand_knowledge


class BrandPanel(forms.Dialog):
    """品牌/车型选择对话框"""

    def __init__(self):
        super(BrandPanel, self).__init__()
        self.Title = "EVOLUTION-AI 品牌造型 DNA"
        self.Resizable = False
        self.Padding = drawing.Padding(12)
        self.Result = None

        self._brands = brand_knowledge.list_brands()

        # ---- 控件 ----
        self.brand_list = forms.DropDown()
        for b in self._brands:
            item = forms.ListItem()
            item.Key = b["key"]
            item.Text = f"{b['zh_name']} {b['name']}"
            self.brand_list.Items.Add(item)

        self.model_list = forms.DropDown()
        self.brand_list.SelectedIndexChanged += self._on_brand_changed

        self.scale_input = forms.NumericUpDown()
        self.scale_input.MinValue = 0.50
        self.scale_input.MaxValue = 1.50
        self.scale_input.Value = 1.00
        self.scale_input.DecimalPlaces = 2
        self.scale_input.Increment = 0.05

        # 车型信息展示
        self.info_label = forms.Label()
        self.info_label.TextAlignment = forms.TextAlignment.Left
        self.model_list.SelectedIndexChanged += self._on_model_changed

        # ---- 按钮 ----
        ok_button = forms.Button()
        ok_button.Text = "生成控制线"
        ok_button.Click += self._on_ok

        cancel_button = forms.Button()
        cancel_button.Text = "取消"
        cancel_button.Click += lambda s, e: self.Close()

        # ---- 布局 ----
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(6, 8)
        layout.BeginVertical()

        layout.AddRow(forms.Label(Text="品牌："), self.brand_list)
        layout.AddRow(forms.Label(Text="车型："), self.model_list)
        layout.AddRow(forms.Label(Text="放缩："), self.scale_input)
        layout.AddRow(None)
        layout.AddRow(self.info_label)
        layout.AddRow(None)
        layout.AddRow(cancel_button, ok_button)

        layout.EndVertical()
        self.Content = layout

        # 初始化首个品牌的车型列表
        self.brand_list.SelectedIndex = 0

    # --------------------------------------------------------
    def _on_brand_changed(self, sender, event):
        """品牌切换 → 重建车型下拉"""
        brand_key = self.brand_list.SelectedKey
        brand = brand_knowledge.get_brand(brand_key)

        self.model_list.Items.Clear()
        for m in brand["models"]:
            item = forms.ListItem()
            item.Key = m["key"]
            item.Text = f"{m['zh_name']} {m['name']}"
            self.model_list.Items.Add(item)
        if self.model_list.Items.Count > 0:
            self.model_list.SelectedIndex = 0

    def _on_model_changed(self, sender, event):
        """车型切换 → 更新参数信息"""
        model = self._selected_model()
        if model is None:
            self.info_label.Text = ""
            return
        p = model["params"]
        self.info_label.Text = (
            f"{model['body_type']}    "
            f"{p['overall_length']} × {p['overall_width']} × {p['overall_height']} mm\n"
            f"轴距 {p['wheelbase']}   姿态指数 {model['metrics']['stance_index']:.2f}"
        )

    def _selected_model(self):
        bk = self.brand_list.SelectedKey
        mk = self.model_list.SelectedKey
        if not bk or not mk:
            return None
        return brand_knowledge.get_model(bk, mk)

    def _on_ok(self, sender, event):
        model = self._selected_model()
        if model is None:
            return
        self.Result = (
            self.brand_list.SelectedKey,
            self.model_list.SelectedKey,
            float(self.scale_input.Value),
        )
        self.Close()


def get_owner_window():
    """获取 Rhino 主窗口（Eto Window），作为模态对话框所有者；
    远程脚本执行环境下没有 owner 时 ShowModal 会立即返回，必须显式传入。"""
    try:
        import Rhino.UI
        return Rhino.UI.RhinoEtoApp.MainWindow
    except Exception:
        return None


def show_panel():
    """打开模态面板，返回 (brand_key, model_key, scale) 或 None"""
    panel = BrandPanel()
    owner = get_owner_window()
    if owner is not None:
        panel.ShowModal(owner)
    else:
        panel.ShowModal()
    return panel.Result
