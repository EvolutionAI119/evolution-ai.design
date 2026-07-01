"""
EVOLUTION AI - 五阶段开发流程图导出为PNG图片
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    os.system(f"{sys.executable} -m pip install Pillow -q")
    from PIL import Image, ImageDraw, ImageFont

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
except ImportError:
    os.system(f"{sys.executable} -m pip install matplotlib -q")
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

import numpy as np

# 颜色方案
COLORS = {
    'bg': '#0a0a1a',
    'phase1': '#1a237e',
    'phase2': '#0d47a1',
    'phase3': '#004d40',
    'phase4': '#1b5e20',
    'phase5': '#bf360c',
    'accent': '#00d4ff',
    'text': '#e0e0e0',
    'text_dim': '#8b9dc3',
    'arrow': '#00d4ff',
    'white': '#ffffff',
}

PHASES = [
    {"id": 1, "name": "Phase 1", "title": "硬点定义", "color": COLORS['phase1'],
     "inputs": "轮心位置 / H点 / 人眼点\nA/C柱角度",
     "core": "前轮心X = FO + WR + 0.08\n后轮心X = L - RO - WR - 0.08\n轮心Y = GC + WR",
     "output": "硬点坐标矩阵",
     "params": "FO · RO · WB · GC\nWR · TW · AA · CA"},
    {"id": 2, "name": "Phase 2", "title": "三曲线系统", "color": COLORS['phase2'],
     "inputs": "硬点坐标\n设计意图",
     "core": "① 侧视轮廓曲线\n② 顶视宽度曲线\n③ 截面变形函数\nsmoothstep G1连续",
     "output": "车身骨架曲线",
     "params": "L · W · H · WL\nWBulge · AA · CA"},
    {"id": 3, "name": "Phase 3", "title": "参数化建模", "color": COLORS['phase3'],
     "inputs": "用户参数调整\nAI推荐参数",
     "core": "14个硬点参数实时驱动\nL→比例  WB→悬分配\nFO→前鼻  RO→车尾\nH→重心   WL→侧面",
     "output": "更新车身曲面",
     "params": "L · W · H · WB\nFO · RO · WL"},
    {"id": 4, "name": "Phase 4", "title": "A级曲面", "color": COLORS['phase4'],
     "inputs": "三曲线输出\n截面数量",
     "core": "50站×16层 Lofted Surface\nG2曲率连续\nF5斑马纹  F6高光\nF7曲率梳",
     "output": "A级曲面",
     "params": "WBulge · AA · CA\nWR · TW"},
    {"id": 5, "name": "Phase 5", "title": "AI辅助设计", "color": COLORS['phase5'],
     "inputs": "自然语言描述\n设计需求",
     "core": "💬 语言参数输入\n🤖 智能参数推荐\n📈 造型趋势分析\n🚀 概念车探索\n🔄 多方案对比",
     "output": "参数方案 / 造型推荐",
     "params": "AI → 参数反馈\n→ Phase 3"},
]


def get_font(size=12, bold=False):
    """获取中文字体"""
    font_names = ['msyh.ttc', 'simhei.ttf', 'simsun.ttc', 'Microsoft YaHei', 'SimHei']
    for fn in font_names:
        try:
            path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', fn)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except:
            pass
    # 尝试其他路径
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except:
            pass
    return ImageFont.load_default()


def hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_rounded_rect(draw, xy, fill, radius=10, outline=None, width=1):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


# ============================================================
# 图1: PPT精简版（横向5列布局）
# ============================================================
def generate_ppt_compact():
    W, H = 2400, 1000
    img = Image.new('RGB', (W, H), hex_to_rgb(COLORS['bg']))
    draw = ImageDraw.Draw(img)

    title_font = get_font(28, True)
    phase_font = get_font(18, True)
    label_font = get_font(12)
    content_font = get_font(11)
    small_font = get_font(10)

    # 标题
    draw.text((W//2, 30), "EVOLUTION AI · 硬点驱动五阶段开发流程", fill=hex_to_rgb(COLORS['accent']),
              font=title_font, anchor='mt')

    # 5个Phase卡片
    card_w = 420
    card_h = 780
    gap = 20
    start_x = (W - 5 * card_w - 4 * gap) // 2
    start_y = 80

    for i, p in enumerate(PHASES):
        x = start_x + i * (card_w + gap)
        y = start_y

        # 卡片背景
        draw_rounded_rect(draw, (x, y, x + card_w, y + card_h),
                         fill=hex_to_rgb(p['color']), radius=12,
                         outline=hex_to_rgb(COLORS['accent']), width=1)

        # Phase标题
        draw.text((x + card_w//2, y + 20), p['name'], fill=hex_to_rgb(COLORS['accent']),
                  font=phase_font, anchor='mt')
        draw.text((x + card_w//2, y + 50), p['title'], fill=hex_to_rgb(COLORS['white']),
                  font=phase_font, anchor='mt')

        # 分隔线
        draw.line([(x + 20, y + 85), (x + card_w - 20, y + 85)],
                  fill=hex_to_rgb(COLORS['accent']), width=1)

        # 输入
        cy = y + 100
        draw.text((x + 20, cy), "📥 输入", fill=hex_to_rgb(COLORS['accent']), font=label_font)
        cy += 22
        for line in p['inputs'].split('\n'):
            draw.text((x + 30, cy), line, fill=hex_to_rgb(COLORS['text']), font=content_font)
            cy += 18

        # 核心
        cy += 15
        draw.text((x + 20, cy), "⚙️ 核心", fill=hex_to_rgb(COLORS['accent']), font=label_font)
        cy += 22
        for line in p['core'].split('\n'):
            draw.text((x + 30, cy), line, fill=hex_to_rgb(COLORS['text']), font=content_font)
            cy += 18

        # 输出
        cy += 15
        draw.text((x + 20, cy), "📤 输出", fill=hex_to_rgb(COLORS['accent']), font=label_font)
        cy += 22
        draw.text((x + 30, cy), p['output'], fill=hex_to_rgb(COLORS['white']), font=content_font)

        # 参数
        cy += 35
        draw.line([(x + 20, cy), (x + card_w - 20, cy)],
                  fill=hex_to_rgb(COLORS['accent']), width=1)
        cy += 10
        draw.text((x + 20, cy), "🔧 参数", fill=hex_to_rgb(COLORS['accent']), font=label_font)
        cy += 22
        for line in p['params'].split('\n'):
            draw.text((x + 30, cy), line, fill=hex_to_rgb(COLORS['text_dim']), font=small_font)
            cy += 16

        # 箭头（Phase间）
        if i < 4:
            ax = x + card_w + 2
            ay = y + card_h // 2
            draw.text((ax, ay), "→", fill=hex_to_rgb(COLORS['arrow']), font=phase_font, anchor='lm')

    # 反馈箭头
    draw.text((W//2, H - 50), "Phase 5 ──参数反馈循环──▶ Phase 3",
              fill=hex_to_rgb(COLORS['accent']), font=label_font, anchor='mt')

    return img


# ============================================================
# 图2: 纵向时间线版
# ============================================================
def generate_timeline():
    W, H = 1200, 2200
    img = Image.new('RGB', (W, H), hex_to_rgb(COLORS['bg']))
    draw = ImageDraw.Draw(img)

    title_font = get_font(26, True)
    phase_font = get_font(20, True)
    label_font = get_font(13)
    content_font = get_font(12)
    small_font = get_font(11)

    # 标题
    draw.text((W//2, 30), "EVOLUTION AI 五阶段开发流程", fill=hex_to_rgb(COLORS['accent']),
              font=title_font, anchor='mt')

    # 时间线
    line_x = 100
    card_x = 160
    card_w = W - card_x - 60
    card_h = 340
    gap = 30

    for i, p in enumerate(PHASES):
        cy_start = 80 + i * (card_h + gap)

        # 时间线圆点
        draw.ellipse((line_x - 12, cy_start + 30 - 12, line_x + 12, cy_start + 30 + 12),
                     fill=hex_to_rgb(p['color']), outline=hex_to_rgb(COLORS['accent']), width=2)

        # 时间线竖线
        if i < 4:
            draw.line([(line_x, cy_start + 42), (line_x, cy_start + card_h + gap - 12)],
                      fill=hex_to_rgb(COLORS['accent']), width=2)

        # 卡片
        draw_rounded_rect(draw, (card_x, cy_start, card_x + card_w, cy_start + card_h),
                         fill=hex_to_rgb(p['color']), radius=12,
                         outline=hex_to_rgb(COLORS['accent']), width=1)

        # 标题
        draw.text((card_x + 20, cy_start + 15), f"{p['name']}: {p['title']}",
                  fill=hex_to_rgb(COLORS['white']), font=phase_font)

        # 分隔线
        draw.line([(card_x + 15, cy_start + 50), (card_x + card_w - 15, cy_start + 50)],
                  fill=hex_to_rgb(COLORS['accent']), width=1)

        # 内容
        cy = cy_start + 60
        sections = [
            ("📌 目标", p['inputs']),
            ("⚙️ 核心", p['core']),
            ("📤 输出", p['output']),
            ("🔧 参数", p['params']),
        ]
        for label, content in sections:
            draw.text((card_x + 20, cy), label, fill=hex_to_rgb(COLORS['accent']), font=label_font)
            cy += 20
            for line in content.split('\n'):
                draw.text((card_x + 35, cy), line, fill=hex_to_rgb(COLORS['text']), font=content_font)
                cy += 17
            cy += 8

    # 反馈箭头
    fy = 80 + 4 * (card_h + gap) + card_h + 20
    draw.text((W//2, fy), "Phase 5 ──参数反馈循环──▶ Phase 3",
              fill=hex_to_rgb(COLORS['accent']), font=label_font, anchor='mt')

    return img


# ============================================================
# 图3: 数据流图
# ============================================================
def generate_dataflow():
    W, H = 1800, 900
    img = Image.new('RGB', (W, H), hex_to_rgb(COLORS['bg']))
    draw = ImageDraw.Draw(img)

    title_font = get_font(26, True)
    phase_font = get_font(18, True)
    label_font = get_font(13)
    content_font = get_font(11)
    arrow_font = get_font(14)

    draw.text((W//2, 25), "EVOLUTION AI 数据流图", fill=hex_to_rgb(COLORS['accent']),
              font=title_font, anchor='mt')

    # 5个节点布局
    positions = [
        (150, 200),   # Phase 1
        (650, 200),   # Phase 2
        (1150, 200),  # Phase 3
        (150, 550),   # Phase 4
        (650, 550),   # Phase 5
    ]

    box_w = 380
    box_h = 250

    for i, (p, (bx, by)) in enumerate(zip(PHASES, positions)):
        draw_rounded_rect(draw, (bx, by, bx + box_w, by + box_h),
                         fill=hex_to_rgb(p['color']), radius=12,
                         outline=hex_to_rgb(COLORS['accent']), width=2)

        draw.text((bx + box_w//2, by + 15), f"{p['name']}: {p['title']}",
                  fill=hex_to_rgb(COLORS['white']), font=phase_font, anchor='mt')

        draw.line([(bx + 15, by + 45), (bx + box_w - 15, by + 45)],
                  fill=hex_to_rgb(COLORS['accent']), width=1)

        cy = by + 55
        draw.text((bx + 15, cy), "输入:", fill=hex_to_rgb(COLORS['accent']), font=label_font)
        draw.text((bx + 60, cy), p['inputs'].replace('\n', ' | '), fill=hex_to_rgb(COLORS['text']), font=content_font)
        cy += 25
        draw.text((bx + 15, cy), "核心:", fill=hex_to_rgb(COLORS['accent']), font=label_font)
        cy += 20
        for line in p['core'].split('\n')[:3]:
            draw.text((bx + 30, cy), line, fill=hex_to_rgb(COLORS['text']), font=content_font)
            cy += 17
        cy += 5
        draw.text((bx + 15, cy), "输出:", fill=hex_to_rgb(COLORS['accent']), font=label_font)
        draw.text((bx + 60, cy), p['output'], fill=hex_to_rgb(COLORS['white']), font=content_font)

    # 箭头: Phase1 → Phase2
    draw.text((545, 310), "硬点参数 ──▶", fill=hex_to_rgb(COLORS['arrow']), font=arrow_font, anchor='rm')
    # 箭头: Phase2 → Phase3
    draw.text((1045, 310), "骨架曲线 ──▶", fill=hex_to_rgb(COLORS['arrow']), font=arrow_font, anchor='rm')
    # 箭头: Phase3 → Phase4
    draw.text((340, 470), "参数驱动", fill=hex_to_rgb(COLORS['arrow']), font=arrow_font, anchor='mt')
    draw.line([(340, 460), (340, 490)], fill=hex_to_rgb(COLORS['arrow']), width=2)
    # 箭头: Phase4 → Phase5
    draw.text((545, 660), "曲面质量 ──▶", fill=hex_to_rgb(COLORS['arrow']), font=arrow_font, anchor='rm')
    # 箭头: Phase5 → Phase3 (反馈)
    draw.text((1150, 660), "AI推荐参数 ──▶ Phase 3", fill=hex_to_rgb(COLORS['accent']), font=arrow_font, anchor='rm')
    draw.line([(1150, 680), (1340, 680), (1340, 460)], fill=hex_to_rgb(COLORS['accent']), width=2)

    return img


# ============================================================
# 图4: Mermaid风格流程图
# ============================================================
def generate_mermaid_style():
    W, H = 2000, 1200
    img = Image.new('RGB', (W, H), hex_to_rgb(COLORS['bg']))
    draw = ImageDraw.Draw(img)

    title_font = get_font(26, True)
    phase_font = get_font(18, True)
    label_font = get_font(12)
    content_font = get_font(11)
    small_font = get_font(10)
    arrow_font = get_font(16, True)

    draw.text((W//2, 20), "EVOLUTION AI · 硬点驱动五阶段开发流程", fill=hex_to_rgb(COLORS['accent']),
              font=title_font, anchor='mt')

    # 上排3个Phase
    top_y = 80
    box_w = 520
    box_h = 450
    top_gap = 40
    top_start = (W - 3 * box_w - 2 * top_gap) // 2

    # 下排2个Phase
    bot_y = top_y + box_h + 80
    bot_start = (W - 2 * box_w - top_gap) // 2

    all_positions = [
        (top_start, top_y),
        (top_start + box_w + top_gap, top_y),
        (top_start + 2 * (box_w + top_gap), top_y),
        (bot_start, bot_y),
        (bot_start + box_w + top_gap, bot_y),
    ]

    for i, (p, (bx, by)) in enumerate(zip(PHASES, all_positions)):
        # 主卡片
        draw_rounded_rect(draw, (bx, by, bx + box_w, by + box_h),
                         fill=hex_to_rgb(p['color']), radius=14,
                         outline=hex_to_rgb(COLORS['accent']), width=2)

        # 标题区
        draw_rounded_rect(draw, (bx, by, bx + box_w, by + 50),
                         fill=hex_to_rgb(p['color']), radius=14)
        draw.text((bx + box_w//2, by + 25), f"{p['name']}: {p['title']}",
                  fill=hex_to_rgb(COLORS['white']), font=phase_font, anchor='mm')

        # 内容区
        cy = by + 60
        sections = [
            ("📥 输入", p['inputs']),
            ("⚙️ 核心", p['core']),
            ("📤 输出", p['output']),
            ("🔧 参数", p['params']),
        ]
        for label, content in sections:
            draw.text((bx + 20, cy), label, fill=hex_to_rgb(COLORS['accent']), font=label_font)
            cy += 18
            for line in content.split('\n'):
                draw.text((bx + 35, cy), line, fill=hex_to_rgb(COLORS['text']), font=content_font)
                cy += 16
            cy += 8

    # 连接箭头
    # Phase1 → Phase2
    ax = top_start + box_w + 5
    ay = top_y + box_h // 2
    draw.text((ax, ay), "→", fill=hex_to_rgb(COLORS['arrow']), font=arrow_font, anchor='lm')
    draw.text((ax + 5, ay - 25), "硬点坐标", fill=hex_to_rgb(COLORS['accent']), font=small_font)

    # Phase2 → Phase3
    ax2 = top_start + 2 * box_w + top_gap + 5
    draw.text((ax2, ay), "→", fill=hex_to_rgb(COLORS['arrow']), font=arrow_font, anchor='lm')
    draw.text((ax2 + 5, ay - 25), "骨架曲线", fill=hex_to_rgb(COLORS['accent']), font=small_font)

    # Phase3 → Phase4 (向下)
    px3 = top_start + 2 * (box_w + top_gap) + box_w // 2
    py3_top = top_y + box_h
    py3_bot = bot_y
    draw.line([(px3, py3_top + 5), (px3, py3_bot - 5)], fill=hex_to_rgb(COLORS['arrow']), width=3)
    draw.text((px3 + 10, (py3_top + py3_bot) // 2), "参数驱动 ↓", fill=hex_to_rgb(COLORS['accent']), font=label_font)

    # Phase4 → Phase5
    ax4 = bot_start + box_w + 5
    ay4 = bot_y + box_h // 2
    draw.text((ax4, ay4), "→", fill=hex_to_rgb(COLORS['arrow']), font=arrow_font, anchor='lm')
    draw.text((ax4 + 5, ay4 - 25), "曲面质量", fill=hex_to_rgb(COLORS['accent']), font=small_font)

    # Phase5 → Phase3 反馈
    px5 = bot_start + 2 * box_w + top_gap + 50
    py5 = bot_y + box_h // 2
    draw.line([(px5, py5), (px5, top_y + box_h // 2), (top_start + 2 * (box_w + top_gap) + box_w + 10, top_y + box_h // 2)],
              fill=hex_to_rgb(COLORS['accent']), width=2)
    draw.text((px5 + 5, (py5 + top_y + box_h // 2) // 2), "参数反馈", fill=hex_to_rgb(COLORS['accent']), font=label_font)

    return img


# ============================================================
# 图5: 概览卡片版（适合封面页）
# ============================================================
def generate_overview():
    W, H = 2400, 600
    img = Image.new('RGB', (W, H), hex_to_rgb(COLORS['bg']))
    draw = ImageDraw.Draw(img)

    title_font = get_font(24, True)
    num_font = get_font(36, True)
    phase_font = get_font(16, True)
    content_font = get_font(10)
    small_font = get_font(9)

    # 标题
    draw.text((W//2, 20), "EVOLUTION AI · 硬点驱动五阶段开发流程", fill=hex_to_rgb(COLORS['accent']),
              font=title_font, anchor='mt')

    # 5个Phase横向排列
    card_w = 420
    card_h = 460
    gap = 25
    start_x = (W - 5 * card_w - 4 * gap) // 2
    start_y = 65

    for i, p in enumerate(PHASES):
        x = start_x + i * (card_w + gap)
        y = start_y

        # 渐变效果：顶部深色，底部浅色
        for row in range(card_h):
            ratio = row / card_h
            base = hex_to_rgb(p['color'])
            lighter = tuple(min(255, int(c + (255 - c) * ratio * 0.3)) for c in base)
            draw.line([(x, y + row), (x + card_w, y + row)], fill=lighter)

        # 圆角遮罩（简化处理，直接画边框）
        draw_rounded_rect(draw, (x, y, x + card_w, y + card_h),
                         fill=None, radius=14,
                         outline=hex_to_rgb(COLORS['accent']), width=2)

        # 大号数字
        draw.text((x + card_w//2, y + 30), str(p['id']), fill=hex_to_rgb(COLORS['accent']),
                  font=num_font, anchor='mt')

        # Phase名称
        draw.text((x + card_w//2, y + 80), p['title'], fill=hex_to_rgb(COLORS['white']),
                  font=phase_font, anchor='mt')

        # 分隔线
        draw.line([(x + 30, y + 110), (x + card_w - 30, y + 110)],
                  fill=hex_to_rgb(COLORS['accent']), width=1)

        # 核心内容（精简）
        cy = y + 125
        for line in p['core'].split('\n'):
            draw.text((x + 25, cy), line, fill=hex_to_rgb(COLORS['text']), font=content_font)
            cy += 16

        # 底部参数
        cy = y + card_h - 60
        draw.line([(x + 30, cy), (x + card_w - 30, cy)],
                  fill=hex_to_rgb(COLORS['accent']), width=1)
        cy += 10
        for line in p['params'].split('\n'):
            draw.text((x + 25, cy), line, fill=hex_to_rgb(COLORS['text_dim']), font=small_font)
            cy += 14

        # 箭头
        if i < 4:
            ax = x + card_w + 3
            ay = y + card_h // 2
            draw.text((ax, ay), "▶", fill=hex_to_rgb(COLORS['arrow']), font=phase_font, anchor='lm')

    # 底部反馈说明
    draw.text((W//2, H - 25), "Phase 5 ──参数反馈循环──▶ Phase 3",
              fill=hex_to_rgb(COLORS['accent']), font=content_font, anchor='mt')

    return img


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "output", "flowcharts")
    os.makedirs(output_dir, exist_ok=True)

    generators = [
        ("1_PPT精简版", generate_ppt_compact),
        ("2_纵向时间线", generate_timeline),
        ("3_数据流图", generate_dataflow),
        ("4_Mermaid风格", generate_mermaid_style),
        ("5_概览卡片版", generate_overview),
    ]

    for name, gen_func in generators:
        print(f"生成 {name}...")
        img = gen_func()
        path = os.path.join(output_dir, f"{name}.png")
        img.save(path, 'PNG', quality=95)
        size_kb = os.path.getsize(path) / 1024
        print(f"  → {path} ({size_kb:.0f} KB, {img.size[0]}×{img.size[1]})")

    print(f"\n全部完成！输出目录: {output_dir}")


if __name__ == "__main__":
    main()
