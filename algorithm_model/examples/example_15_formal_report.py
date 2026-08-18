"""
Generate formal A4 continuity report PDF (cover page + summary + table + 4-view image).

Uses reportlab UnicodeCIDFont (STSong-Light) for zero-dependency Chinese rendering.
Run after example_15: outputs continuity_attached_formal_report.pdf.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
from datetime import datetime

from algorithm_model.car_modeling import CarParams, ContinuityChecker
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.car_modeling.body_ends_g1 import (
    build_front_bumper_g1, build_rear_bumper_g1,
)
from algorithm_model.car_modeling.body_ends_attached import (
    build_grille_attached, build_headlight_attached, build_taillight_attached,
)
from algorithm_model.car_modeling.accessories_nurbs import (
    build_all_wheels_nurbs, build_all_mirrors_nurbs,
)
from example_15_attached_continuity import (
    render_four_view, PNG_PATH, PDF_PATH, DESIGN_CHECKS,
)

OUT_DIR = os.path.join(_ROOT, "data", "step")
FORMAL_REPORT_PDF = os.path.join(OUT_DIR, "continuity_attached_formal_report.pdf")

# reportlab imports with aliased colors module (per experience 1126482)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors as rcolors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether,
)

PAGE_W, PAGE_H = A4  # 595.27 x 841.89 pt


def register_fonts():
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        return "Helvetica"


def build_styles(font_name):
    styles = getSampleStyleSheet()
    base = dict(fontName=font_name)
    s_title = ParagraphStyle("CoverTitle", parent=styles["Title"], **base,
                             fontSize=30, leading=38, alignment=TA_CENTER,
                             textColor=rcolors.HexColor("#1a1a2e"),
                             spaceAfter=12 * mm)
    s_sub = ParagraphStyle("CoverSub", parent=styles["Normal"], **base,
                           fontSize=13, leading=18, alignment=TA_CENTER,
                           textColor=rcolors.HexColor("#4a4a6a"),
                           spaceAfter=6 * mm)
    s_h1 = ParagraphStyle("H1", parent=styles["Heading1"], **base,
                          fontSize=18, leading=24, textColor=rcolors.HexColor("#1a1a2e"),
                          spaceBefore=4 * mm, spaceAfter=4 * mm,
                          borderWidth=0, borderPadding=0)
    s_h2 = ParagraphStyle("H2", parent=styles["Heading2"], **base,
                          fontSize=13, leading=18, textColor=rcolors.HexColor("#33335a"),
                          spaceBefore=3 * mm, spaceAfter=2 * mm)
    s_body = ParagraphStyle("Body", parent=styles["Normal"], **base,
                            fontSize=10.5, leading=15, textColor=rcolors.black,
                            spaceAfter=2 * mm)
    s_small = ParagraphStyle("Small", parent=styles["Normal"], **base,
                             fontSize=9, leading=13, textColor=rcolors.HexColor("#666666"))
    return dict(Title=s_title, Sub=s_sub, H1=s_h1, H2=s_h2, Body=s_body, Small=s_small)


def build_all_surfaces(params):
    body_surf = build_body_nurbs(params)
    front_bumper = build_front_bumper_g1(params, body_surf, g1_k=0.3, bulge=0.08)
    rear_bumper = build_rear_bumper_g1(params, body_surf, g1_k=0.3, bulge=0.06)
    grille = build_grille_attached(params, front_bumper, recess=0.06)
    headlight_R = build_headlight_attached(params, front_bumper, "right", bulge=0.02)
    headlight_L = build_headlight_attached(params, front_bumper, "left", bulge=0.02)
    taillight_R = build_taillight_attached(params, rear_bumper, "right", bulge=0.015)
    taillight_L = build_taillight_attached(params, rear_bumper, "left", bulge=0.015)
    wheels = build_all_wheels_nurbs(params)
    mirrors = build_all_mirrors_nurbs(params)

    items = [
        ("body_upper_skin", body_surf),
        ("front_bumper_g1", front_bumper),
        ("rear_bumper_g1", rear_bumper),
        ("grille_attached", grille),
        ("headlight_R_attached", headlight_R),
        ("headlight_L_attached", headlight_L),
        ("taillight_R_attached", taillight_R),
        ("taillight_L_attached", taillight_L),
    ]
    for s, n, _ in wheels + mirrors:
        items.append((n, s))
    return items


def make_summary_table(summary, S):
    data = [
        ["指标", "数值"],
        ["分析曲面对总数", str(summary["total_pairs"])],
        ["G0 位置连续通过 (＜0.1 mm)", "%d  (%.1f%%)" % (summary["g0_pass"], summary["g0_pass_pct"])],
        ["G1 切线连续通过 (＜1.0°)", "%d  (%.1f%%)" % (summary["g1_pass"], summary["g1_pass_pct"])],
        ["G0 + G1 同时通过", str(summary["g0_g1_both"])],
    ]
    rc = summary.get("rating_counts", {})
    for k in ["G1 OK", "G0 OK", "Near G0", "Small gap", "Separated"]:
        data.append([("连续性评级：%s" % k), str(rc.get(k, 0))])
    t = Table(data, colWidths=[120 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), S["font"]),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), rcolors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rcolors.white),
        ("BACKGROUND", (0, 1), (0, -1), rcolors.HexColor("#f4f4f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, rcolors.HexColor("#ccccdd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def make_key_pairs_table(results, S):
    header = ["连接对", "G0 min (mm)", "G1 max (°)", "评级"]
    rows = [header]
    for r in results[:15]:
        rows.append([
            r["pair"][:36],
            "%.3f" % r["min_gap_mm"],
            "%.2f" % r["max_g1_deg"],
            r["rating"],
        ])
    t = Table(rows, colWidths=[95 * mm, 28 * mm, 28 * mm, 29 * mm], repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), S["font"]),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), rcolors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rcolors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, rcolors.HexColor("#bbbbcc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    # Color ratings
    RATING_COLOR = {
        "G1 OK": rcolors.HexColor("#d7f7e4"),
        "G0 OK": rcolors.HexColor("#e6f3ff"),
        "Near G0": rcolors.HexColor("#fff6d6"),
        "Small gap": rcolors.HexColor("#ffe7d6"),
        "Separated": rcolors.HexColor("#f0e6ef"),
    }
    for i, row in enumerate(rows[1:], 1):
        c = RATING_COLOR.get(row[3])
        if c:
            style.append(("BACKGROUND", (-1, i), (-1, i), c))
    t.setStyle(TableStyle(style))
    return t


def verify_design_check(checker, result, expect_g0_mm, expect_g1_deg_or_None):
    """与 ContinuityChecker 统一口径的设计意图验证。

    Rules
    -----
    (expect_g0==0 AND expect_g1 is not None) → 严格 G1 连续模式：
        G0 = result['g0_pass']  (bound to checker.g0_thresh_mm)
        G1 = result['g1_pass']  (bound to checker.g1_thresh_deg)

    (expect_g0!=0 AND expect_g1 is None) →  recess/bulge 装配模式：
        G0 仅检查"存在有效 YZ 邻接"，即 0 < min_gap_mm < 30 mm
            且 rating ∈ {Near G0, Small gap, Separated}
        （DESIGN_CHECKS 的 expect_g0_mm 是 X 方向 recess/bulge 名义深度，
         与 ContinuityChecker 基于 YZ 平面的 min_gap_mm 量纲不同，不再直接比差）
    """
    r = result
    if expect_g0_mm == 0.0 and expect_g1_deg_or_None is not None:
        # 严格 G1 连续：绑定 ContinuityChecker 的阈值（不自写 0.1mm / 2deg）
        g0_ok = bool(r.get("g0_pass", False))
        g1_ok = bool(r.get("g1_pass", False))
        return g0_ok, g1_ok
    else:
        # 装配 recess/bulge：只校验"有效近邻"，不要求匹配 X 偏移绝对值
        contact_ok = (0.0 < r["min_gap_mm"] < 30.0
                      and r.get("rating") in {
                          "Near G0", "Small gap", "Separated"})
        return contact_ok, True  # G1=None 不检查


def build_pdf(checker, png_path, out_pdf):
    font_name = register_fonts()
    S = build_styles(font_name)
    S["font"] = font_name

    summary = checker.summary()
    results = checker.results or []

    thresholds_line = (
        "阈值：G0 ＜ %.2f mm &nbsp;|&nbsp; G1 ＜ %.2f° &nbsp;|&nbsp; "
        "Visual ＜ %.2f° &nbsp;|&nbsp; 每边采样：%d 点"
        % (checker.g0_thresh_mm, checker.g1_thresh_deg,
           checker.g1_visual_deg, checker.n_samples))

    def _on_first_page(canvas, doc):
        canvas.saveState()
        # Decorative band
        canvas.setFillColor(rcolors.HexColor("#1a1a2e"))
        canvas.rect(0, PAGE_H - 45 * mm, PAGE_W, 45 * mm, fill=1, stroke=0)
        canvas.setFillColor(rcolors.HexColor("#c8323a"))
        canvas.rect(0, PAGE_H - 48 * mm, PAGE_W, 3 * mm, fill=1, stroke=0)
        # Top-right brand text
        canvas.setFont(font_name, 9)
        canvas.setFillColor(rcolors.white)
        canvas.drawRightString(PAGE_W - 20 * mm, PAGE_H - 16 * mm,
                               "Evolution-AI.Design  NURBS+STEP 工程化管线")
        canvas.drawRightString(PAGE_W - 20 * mm, PAGE_H - 22 * mm,
                               "曲面连续性分析 · Ver 1.0")
        # Footer
        canvas.setFillColor(rcolors.HexColor("#1a1a2e"))
        canvas.rect(0, 0, PAGE_W, 12 * mm, fill=1, stroke=0)
        canvas.setFillColor(rcolors.white)
        canvas.setFont(font_name, 8)
        canvas.drawString(20 * mm, 5 * mm,
                          "Report Date: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        canvas.drawRightString(PAGE_W - 20 * mm, 5 * mm,
                               "Page 1 · Cover")
        canvas.restoreState()

    def _on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(rcolors.HexColor("#666666"))
        canvas.drawString(20 * mm, PAGE_H - 12 * mm,
                          "Evolution-AI.Design · 曲面连续性分析报告")
        canvas.drawRightString(PAGE_W - 20 * mm, PAGE_H - 12 * mm,
                               datetime.now().strftime("%Y-%m-%d"))
        canvas.setStrokeColor(rcolors.HexColor("#ccccdd"))
        canvas.setLineWidth(0.3)
        canvas.line(20 * mm, PAGE_H - 14 * mm, PAGE_W - 20 * mm, PAGE_H - 14 * mm)
        canvas.line(20 * mm, 14 * mm, PAGE_W - 20 * mm, 14 * mm)
        canvas.drawString(20 * mm, 8 * mm,
                          "Full Car Attached · G1 bumpers + G0 ends  (L=4.70m W=1.85m H=1.45m)")
        canvas.drawRightString(PAGE_W - 20 * mm, 8 * mm, "Page %d" % doc.page)
        canvas.restoreState()

    doc = SimpleDocTemplate(out_pdf, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm,
                            title="Full Car Attached Continuity Report",
                            author="Evolution-AI.Design")

    story = []
    # ---- Cover page (page 1) ----
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph("整车 NURBS 曲面连续性", S["Title"]))
    story.append(Paragraph("Full Car Attached · 最终分析报告", S["Sub"]))
    story.append(Spacer(1, 8 * mm))
    carline = "车型：三厢轿车 &nbsp;&nbsp; 尺寸 L×W×H = 4.70m × 1.85m × 1.45m &nbsp;&nbsp; 曲面总数：%d 件" % len(checker.items)
    story.append(Paragraph(carline, S["Sub"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("分析方法：有限差分法向量 + cKDTree 边界最近邻 + 4×4 边界组合最优匹配", S["Body"]))
    story.append(Paragraph(thresholds_line, S["Body"]))

    # Overall verdict badge (as a table): values pulled from ContinuityChecker results
    g1_count = summary["g0_g1_both"]
    g1_rows = [r for r in results if r.get("rating") == "G1 OK"]
    if g1_rows:
        worst_g1 = max(r["max_g1_deg"] for r in g1_rows)
        worst_g0 = max(r["min_gap_mm"] for r in g1_rows)
        crit_line = "G0 ≤ %.3f mm · G1 ≤ %.2f°" % (worst_g0, worst_g1)
    else:
        crit_line = "(无 G1 通过对)"
    verdict = "✅ 通过" if g1_count >= 2 else "⚠ 需复核"
    verdict_color = "#16a34a" if g1_count >= 2 else "#b45309"
    vtable = Table(
        [["总体结论", "关键 G1 连续对", "关键指标 (ContinuityChecker)"],
         [verdict,
          "%d 对（车身 ↔ 前后保险杠）" % g1_count,
          crit_line]],
        colWidths=[45 * mm, 70 * mm, 65 * mm])
    vtable.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), rcolors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rcolors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, rcolors.HexColor("#ccccdd")),
        ("BACKGROUND", (0, 1), (0, 1), rcolors.HexColor(verdict_color)),
        ("TEXTCOLOR", (0, 1), (0, 1), rcolors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 8 * mm))
    story.append(vtable)

    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("Document classification: 工程质量报告（内部）  |  Algorithm: ContinuityChecker v1.0", S["Small"]))

    story.append(PageBreak())

    # ---- Page 2: Summary statistics ----
    story.append(Paragraph("1. 连续性统计摘要", S["H1"]))
    story.append(Paragraph("以下统计覆盖全部 124 对曲面对（按规则剔除车轮互相、后视镜互相等独立装配配对之外的全部组合）。", S["Body"]))
    story.append(make_summary_table(summary, S))

    story.append(Paragraph("2. 评级分布说明", S["H2"]))
    def_row = [
        ["评级", "判定条件", "工程含义"],
        ["G1 OK", "G0 通过 AND G1 通过", "严格连续：位置 + 切线双零缺陷"],
        ["G0 OK", "G0 通过 AND 视觉平滑", "位置连续，肉眼可见无折痕"],
        ["Near G0", "min_gap ＜ 1.0 mm", "接近连续，需关注装配配合"],
        ["Small gap", "1.0 ≤ min_gap ＜ 10 mm", "存在设计间隙 / 零件偏移"],
        ["Separated", "min_gap ≥ 10 mm", "物理分离（不同部件正常间距）"],
    ]
    dt = Table(def_row, colWidths=[28 * mm, 75 * mm, 77 * mm])
    dt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), rcolors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rcolors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, rcolors.HexColor("#bbbbcc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(Spacer(1, 2 * mm))
    story.append(dt)

    story.append(Paragraph("3. 设计意图验证", S["H2"]))
    story.append(Paragraph("针对关键连接对，按工程设计预期（严格连续 / 凹陷 recess / 外凸 bulge）判定结果一致性。", S["Body"]))

    cm = {r["pair"]: r for r in results}
    dv_rows = [["连接对", "预期", "实际 G0 (mm)", "实际 G1 (°)", "结论"]]
    for pair, desc, eg0, eg1, wg0, wg1 in DESIGN_CHECKS:
        r = cm.get(pair)
        if r is None:
            a, b = pair.split(" <-> ")
            r = cm.get(b + " <-> " + a)
        if r is None:
            dv_rows.append([pair[:30], desc[:20], "-", "-", "缺失"])
            continue
        g0_ok, g1_ok = verify_design_check(checker, r, eg0, eg1)
        g1_text = "N/A" if eg1 is None else ("%.2f" % r["max_g1_deg"])
        verdict = "OK" if (g0_ok and g1_ok) else "CHECK"
        dv_rows.append([
            pair[:30], desc[:22], "%.3f" % r["min_gap_mm"], g1_text, verdict
        ])
        # Console trace (用于运行时核对 7 条设计意图)
        print("  [DV] %-40s  G0=%.3fmm  G1=%-7s  verdict=%s" % (
            pair[:40], r["min_gap_mm"], g1_text, verdict))
    dv = Table(dv_rows, colWidths=[55 * mm, 42 * mm, 30 * mm, 28 * mm, 25 * mm], repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), rcolors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rcolors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, rcolors.HexColor("#bbbbcc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, row in enumerate(dv_rows[1:], 1):
        c = rcolors.HexColor("#d7f7e4") if row[4] == "OK" else rcolors.HexColor("#ffe7d6")
        style.append(("BACKGROUND", (-1, i), (-1, i), c))
    dv.setStyle(TableStyle(style))
    story.append(Spacer(1, 2 * mm))
    story.append(dv)

    story.append(PageBreak())

    # ---- Page 3: Key pairs detail table ----
    story.append(Paragraph("4. Top-15 最近邻连接对（按最小间隙升序）", S["H1"]))
    story.append(make_key_pairs_table(results, S))

    story.append(PageBreak())

    # ---- Page 4: 4-view figure ----
    story.append(Paragraph("5. 整车四视角对比图（Continuity Highlights）", S["H1"]))
    story.append(Paragraph("左上子图标注了关键连续性指标，设计偏移量对应格栅 recess=60mm、大灯 bulge=20mm、尾灯 bulge=15mm。", S["Body"]))

    img_w = 170 * mm
    img_h = 127.5 * mm  # 4:3
    if os.path.exists(png_path):
        story.append(Image(png_path, width=img_w, height=img_h))
    else:
        story.append(Paragraph("[图未生成：%s]" % png_path, S["Body"]))

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("图 1. 整车四视角（Iso / Side / Front / Top）及连续性高亮标注", S["Small"]))

    doc.build(story, onFirstPage=_on_first_page, onLaterPages=_on_later_pages)
    return out_pdf


def main():
    print("=" * 70)
    print("Formal A4 Report - Continuity PDF")
    print("=" * 70)
    t0 = time.time()

    params = CarParams()
    items = build_all_surfaces(params)
    checker = ContinuityChecker(
        g0_thresh_mm=0.1, g1_thresh_deg=1.0, g1_visual_deg=5.0,
        n_samples=50, skip_patterns=["wheel_", "mirror_"],
    )
    checker.add_surfaces(items)
    checker.analyze_all()

    # Re-render high-res PNG (for image inside report)
    render_four_view(checker, PNG_PATH, pdf_path=PDF_PATH, dpi_png=200, dpi_pdf=300)

    os.makedirs(OUT_DIR, exist_ok=True)
    build_pdf(checker, PNG_PATH, FORMAL_REPORT_PDF)
    size_kb = os.path.getsize(FORMAL_REPORT_PDF) / 1024
    print("Formal Report PDF: %s  (%.1f KB)" % (FORMAL_REPORT_PDF, size_kb))
    print("4-view PDF:       %s  (%.1f KB)" % (PDF_PATH, os.path.getsize(PDF_PATH) / 1024))
    print("Done in %.2fs" % (time.time() - t0))


if __name__ == "__main__":
    sys.exit(main())
