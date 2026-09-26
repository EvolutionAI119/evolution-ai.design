# -*- coding: utf-8 -*-
"""
EVOLUTION-AI × Rhino：调用本机 Web API 实现语义融合
====================================================

本脚本在 Rhino 8 (Script Editor / CPython 3) 中运行，通过 HTTP 调用本机后端
（http://127.0.0.1:8000），把"纹样图 → CLIP 语义分析 → 自动调参"的完整能力
引入 Rhino，而无需在 Rhino 内嵌 Python 中安装 torch/transformers（约 600MB）。

工作流：
  1. 健康检查 GET  /api/v1/texture/regions        （确认后端在线、CLIP 语义可用）
  2. 语义分析 POST /api/v1/texture/analyze        （仅分析：返回 6 轴风格分数 + 参数覆盖）
  3. 直接应用 POST /api/v1/texture/apply/{sid}    （应用到会话并由后端渲染预览点云）
     └─ 会话由 POST /api/v1/import-export/import 创建
  4. 预览点云自动落入 Rhino 文档图层 EVOLUTION-AI::API-Preview

特点：
  - 零第三方依赖：仅用标准库 urllib/json/uuid + Rhino API + Eto
    （手写 multipart/form-data，不依赖 requests）
  - 后端不可达时给出明确的启动指引
  - 支持 use_semantic 开关与 semantic_weight 调节

前置条件：
  - 本机后端已启动：
      cd backend
      $env:SESSION_USE_REDIS="true"
      python start.py
  - 首次语义分析需后端已缓存 CLIP 权重（safetensors）

使用：Rhino 8 → Ctrl+Alt+N → 粘贴本脚本 → Run
"""
from __future__ import annotations

import json
import mimetypes
import uuid
import urllib.error
import urllib.request
from pathlib import Path

# ============================================================
# Rhino 运行时
# ============================================================
try:
    import Rhino
    import rhinoscriptsyntax as rs
    import scriptcontext as sc
    import Eto
    import Eto.Forms as forms
    import Eto.Drawing as drawing
    RHINO_AVAILABLE = True
except ImportError:
    RHINO_AVAILABLE = False
    class _DummyModule:
        def __getattr__(self, name):
            class _Cls:
                def __init__(self, *a, **k): pass
                def __getattr__(self, n): return _Cls()
                def __call__(self, *a, **k): return _Cls()
            return _Cls
    forms = drawing = _DummyModule()
    print("[WARNING] 未检测到 Rhino 运行时，本脚本需在 Rhino 8 Script Editor 中运行。")


# ============================================================
# 配置
# ============================================================

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
PREVIEW_LAYER = "EVOLUTION-AI::API-Preview"
HTTP_TIMEOUT = 120  # 秒；首次加载 CLIP 可能较慢


# ============================================================
# API 客户端（标准库实现）
# ============================================================

class EvolutionAIAPIClient:
    """EVOLUTION-AI 本机 Web API 客户端（仅用 urllib，无第三方依赖）"""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")

    # ---------- 底层 HTTP ----------

    def _get_json(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post_json(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _build_multipart(fields: dict, file_field: str, filename: str,
                         file_bytes: bytes) -> tuple[bytes, str]:
        """手写 multipart/form-data 请求体

        Args:
            fields: 普通表单字段 {name: value}（value 会转为字符串）
            file_field: 文件字段名
            filename: 文件名
            file_bytes: 文件二进制内容

        Returns:
            (body_bytes, content_type_header)
        """
        boundary = uuid.uuid4().hex
        lines = []
        for name, value in fields.items():
            lines.append(f"--{boundary}".encode("utf-8"))
            lines.append(
                f'Content-Disposition: form-data; name="{name}"'.encode("utf-8")
            )
            lines.append(b"")
            lines.append(str(value).encode("utf-8"))
        # 文件部分
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{filename}"'.encode("utf-8")
        )
        lines.append(f"Content-Type: {ctype}".encode("utf-8"))
        lines.append(b"")
        body = b"\r\n".join(lines) + b"\r\n" + file_bytes + \
               b"\r\n" + f"--{boundary}--\r\n".encode("utf-8")
        return body, f"multipart/form-data; boundary={boundary}"

    def _post_multipart(self, path: str, fields: dict, file_field: str,
                        filename: str, file_bytes: str) -> dict:
        url = f"{self.base_url}{path}"
        body, ctype = self._build_multipart(fields, file_field, filename, file_bytes)
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": ctype},
        )
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ---------- 业务接口 ----------

    def health_check(self) -> dict:
        """GET /api/v1/texture/regions：后端在线性 + CLIP 语义可用性"""
        return self._get_json("/api/v1/texture/regions")

    def create_session(self, name: str | None = None) -> dict:
        """POST /api/v1/import-export/import：创建参数会话"""
        return self._post_json("/api/v1/import-export/import", {"name": name})

    def analyze_texture(self, image_path: str, target_region: str, intensity: float,
                        use_semantic: bool = True,
                        semantic_weight: float = 0.4) -> dict:
        """POST /api/v1/texture/analyze：语义融合分析（不落会话）"""
        p = Path(image_path)
        file_bytes = p.read_bytes()
        return self._post_multipart(
            "/api/v1/texture/analyze",
            fields={
                "target_region": target_region,
                "intensity": intensity,
                "use_semantic": "true" if use_semantic else "false",
                "semantic_weight": semantic_weight,
            },
            file_field="image",
            filename=p.name,
            file_bytes=file_bytes,
        )

    def apply_texture(self, session_id: str, image_path: str, target_region: str,
                      intensity: float, use_semantic: bool = True,
                      semantic_weight: float = 0.4,
                      auto_render: bool = True) -> dict:
        """POST /api/v1/texture/apply/{sid}：应用到会话并由后端渲染预览"""
        p = Path(image_path)
        file_bytes = p.read_bytes()
        return self._post_multipart(
            f"/api/v1/texture/apply/{session_id}",
            fields={
                "target_region": target_region,
                "intensity": intensity,
                "use_semantic": "true" if use_semantic else "false",
                "semantic_weight": semantic_weight,
                "auto_render": "true" if auto_render else "false",
            },
            file_field="image",
            filename=p.name,
            file_bytes=file_bytes,
        )


# ============================================================
# Rhino 文档：预览点云落图
# ============================================================

def _hex_to_color(hex_color: str):
    h = hex_color.lstrip("#")
    return drawing.Color.FromArgb(
        int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    )


def _ensure_layer(name: str):
    doc = sc.doc
    idx = doc.Layers.FindName(name, True)
    if idx < 0:
        layer = Rhino.DocObjects.Layer()
        layer.Name = name
        idx = doc.Layers.Add(layer)
    return idx


def clear_preview_layer():
    """清空 API-Preview 图层上的旧对象"""
    doc = sc.doc
    layer = doc.Layers.FindName(PREVIEW_LAYER, True)
    if layer:
        settings = Rhino.DocObjects.ObjectEnumeratorSettings()
        settings.LayerIndexFilter = layer.Index
        for obj in doc.Objects.GetObjectList(settings):
            doc.Objects.Delete(obj, True)


def draw_preview(preview: dict) -> int:
    """把后端返回的 preview.components 点云落入 Rhino 文档

    preview 结构：
      {"components": [{"name","color","points":[[x,y,z], ...], ...}], "total_surfaces"}
    """
    clear_preview_layer()
    _ensure_layer(PREVIEW_LAYER)
    doc = sc.doc
    count = 0
    for comp in preview.get("components", []):
        pts = comp.get("points") or []
        # points 可能是嵌套网格 [[[x,y,z],...],...]，拍平
        flat = []
        for item in pts:
            if isinstance(item, (list, tuple)) and item and isinstance(item[0], (list, tuple)):
                flat.extend(item)
            else:
                flat.append(item)
        if not flat:
            continue
        pt3d = [Rhino.Geometry.Point3d(float(p[0]), float(p[1]), float(p[2]))
                for p in flat if len(p) >= 3]
        if not pt3d:
            continue
        pcloud = Rhino.Geometry.PointCloud(pt3d)
        attrs = doc.CreateDefaultAttributes()
        attrs.LayerIndex = doc.Layers.FindName(PREVIEW_LAYER, True).Index
        attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        attrs.ObjectColor = _hex_to_color(comp.get("color", "#c0c0c0"))
        doc.Objects.AddPointCloud(pcloud, attrs)
        count += 1
    doc.Views.Redraw()
    return count


# ============================================================
# Eto 参数面板
# ============================================================

class SemanticAPIDialog(forms.Dialog):
    """语义融合参数对话框"""

    def __init__(self, regions: list[str], semantic_available: bool,
                 image_path: str):
        super().__init__()
        self.Title = "EVOLUTION-AI | API 语义融合"
        self.ClientSize = drawing.Size(400, 360)
        self.ok_pressed = False

        layout = forms.DynamicLayout()
        layout.Spacing = drawing.Size(5, 6)
        layout.Padding = drawing.Padding(12)

        title = forms.Label()
        title.Text = "纹样图 → 本机 API → 语义调参"
        title.Font = drawing.Font(None, 13, drawing.FontStyle.Bold)
        layout.AddRow(title)

        img_label = forms.Label()
        img_label.Text = f"纹样: {Path(image_path).name}"
        img_label.TextColor = drawing.Color.FromArgb(80, 80, 80)
        layout.AddRow(img_label)

        sem_label = forms.Label()
        sem_label.Text = ("CLIP 语义: 可用 ✓" if semantic_available
                          else "CLIP 语义: 不可用（将仅用几何特征）")
        sem_label.TextColor = drawing.Color.FromArgb(0, 120, 0) if semantic_available \
            else drawing.Color.FromArgb(200, 120, 0)
        layout.AddRow(sem_label)
        layout.AddRow(None)

        # 目标部位
        layout.AddRow(forms.Label(Text="目标部位："))
        self.ddl_region = forms.DropDown()
        for r in regions:
            self.ddl_region.Items.Add(r)
        self.ddl_region.SelectedIndex = 0
        layout.AddRow(self.ddl_region)

        # 调参强度
        self.lbl_intensity = forms.Label(Text="调参强度：0.50")
        self.slider_intensity = forms.Slider()
        self.slider_intensity.MinValue, self.slider_intensity.MaxValue = 0, 100
        self.slider_intensity.Value = 50
        self.slider_intensity.ValueChanged += lambda s, e: self.lbl_intensity.set_Text(
            f"调参强度：{s.Value / 100.0:.2f}")
        layout.AddRow(self.lbl_intensity)
        layout.AddRow(self.slider_intensity)

        # 语义权重
        self.lbl_weight = forms.Label(Text="语义权重：0.40（仅语义可用时）")
        self.slider_weight = forms.Slider()
        self.slider_weight.MinValue, self.slider_weight.MaxValue = 0, 100
        self.slider_weight.Value = 40
        self.slider_weight.ValueChanged += lambda s, e: self.lbl_weight.set_Text(
            f"语义权重：{s.Value / 100.0:.2f}（仅语义可用时）")
        layout.AddRow(self.lbl_weight)
        layout.AddRow(self.slider_weight)

        # 是否创建会话并渲染预览
        self.chk_apply = forms.CheckBox()
        self.chk_apply.Text = "创建会话、应用参数并由后端渲染预览点云（推荐）"
        self.chk_apply.Checked = True
        layout.AddRow(self.chk_apply)
        layout.AddRow(None)

        # 按钮
        btn_row = forms.StackLayout()
        btn_row.Orientation = forms.Orientation.Horizontal
        btn_row.Spacing = 8
        btn_ok = forms.Button(Text="开始分析")
        btn_ok.Click += self._on_ok
        btn_cancel = forms.Button(Text="取消")
        btn_cancel.Click += lambda s, e: self.Close()
        btn_row.Items.Add(btn_ok)
        btn_row.Items.Add(btn_cancel)
        layout.AddRow(btn_row)

        self.Content = layout

    def _on_ok(self, sender, e):
        self.ok_pressed = True
        self.Close()


# ============================================================
# 结果展示
# ============================================================

def print_semantic_result(result: dict):
    """把语义分析结果打印到 Rhino 命令行"""
    print("=" * 62)
    sem = result.get("semantic")
    if sem:
        print("【CLIP 语义特征】")
        axis_labels = {
            "sportiness": "运动感", "luxury": "豪华感", "futurism": "科技感",
            "angularity": "硬朗感", "minimalism": "简约感", "organic": "自然感",
        }
        for key, label in axis_labels.items():
            v = sem[key]
            bar = "#" * int(v * 24)
            print(f"  {label}({key:10s}) {v:.3f} [{bar:<24s}]")
        print(f"  显著度: {sem['confidence']:.3f}")
        kws = sem.get("style_keywords", [])[:3]
        print(f"  风格关键词: {kws}")
    else:
        print("【语义未启用，仅几何特征】")
    print(f"  调参项数: {result['param_count']}")
    for group, items in result.get("overrides", {}).items():
        print(f"  [{group}]")
        for k, v in items.items():
            print(f"    {k} = {v}")
    print("=" * 62)


# ============================================================
# 主流程
# ============================================================

def main(base_url: str = DEFAULT_BASE_URL):
    if not RHINO_AVAILABLE:
        print("[ERROR] 本脚本必须在 Rhino 8 Script Editor 中运行。")
        return

    client = EvolutionAIAPIClient(base_url)

    # 1. 选择纹样图
    image_path = rs.OpenFileName(
        title="选择设计纹样图",
        filter="图片文件 (*.png;*.jpg;*.jpeg;*.bmp)|*.png;*.jpg;*.jpeg;*.bmp",
    )
    if not image_path:
        print("已取消。")
        return

    # 2. 健康检查
    print(f"正在连接本机 API: {base_url} ...")
    try:
        info = client.health_check()
    except urllib.error.URLError:
        print(f"[ERROR] 无法连接 {base_url}。请先启动本机后端：")
        print("        cd backend")
        print('        $env:SESSION_USE_REDIS="true"')
        print("        python start.py")
        return

    regions = info["regions"]
    semantic_ok = bool(info["semantic"]["available"])
    print(f"后端在线 ✓ CLIP 语义: {'可用' if semantic_ok else '不可用'}")

    # 3. 参数对话框
    dlg = SemanticAPIDialog(regions, semantic_ok, image_path)
    dlg.ShowModal()
    if not dlg.ok_pressed:
        print("已取消。")
        return

    region = dlg.ddl_region.SelectedValue
    intensity = dlg.slider_intensity.Value / 100.0
    weight = dlg.slider_weight.Value / 100.0
    do_apply = bool(dlg.chk_apply.Checked)

    # 4. 调用 API
    if do_apply:
        # 创建会话
        session = client.create_session(name=f"Rhino-{Path(image_path).stem}")
        sid = session["session_id"]
        print(f"已创建会话: {sid}（{session['param_count']} 个参数）")

        print("正在应用语义融合并渲染预览（首次加载 CLIP 可能需数十秒）...")
        result = client.apply_texture(
            sid, image_path, region, intensity,
            use_semantic=semantic_ok, semantic_weight=weight, auto_render=True,
        )
        print_semantic_result(result)

        # 5. 预览点云落 Rhino 文档
        if result.get("rendered") and result.get("preview"):
            n = draw_preview(result["preview"])
            print(f"✅ 预览点云已落入图层 [{PREVIEW_LAYER}]，共 {n} 个部件")
            print(f"   会话ID {sid} 可继续通过 API 改参/导出 STEP 等")
        elif result.get("render_error"):
            print(f"⚠ 后端渲染失败: {result['render_error']}")
    else:
        print("正在进行语义融合分析（不落会话）...")
        result = client.analyze_texture(
            image_path, region, intensity,
            use_semantic=semantic_ok, semantic_weight=weight,
        )
        print_semantic_result(result)
        print("✅ 分析完成（勾选对话框选项可创建会话并渲染预览）")


if __name__ == "__main__":
    main()
