"""生成 10 月审计/测试报告的标准化可视化图表（SVG，零依赖，GitHub Pages 兼容）。
设计系统继承 docs/images/ 已有图表：深色主题 + 四色强调。
运行: python tools/gen_october_charts.py
"""
import math
import os
import re
from xml.sax.saxutils import escape as _esc

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "images")
os.makedirs(OUT, exist_ok=True)

# ── 设计令牌 ──────────────────────────────────────────────
BG = "#0F1622"
BORDER = "#1E2A3A"
PANEL = "#0B101A"
TEXT = "#E2E8F0"
SUB = "#94A3B8"
MUTED = "#64748B"
LABEL = "#CBD5E1"
GREEN, GREEN_LIGHT = "#34D399", "#6EE7B7"
BLUE, BLUE_LIGHT = "#38BDF8", "#7DD3FC"
PURPLE, PURPLE_LIGHT = "#A78BFA", "#C4B5FD"
YELLOW, YELLOW_LIGHT = "#FBBF24", "#FCD34D"
RED = "#F87171"

W, H = 960, 440


def header(title, en, dot=GREEN):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="'Segoe UI','Microsoft YaHei',system-ui,sans-serif">
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{BG}" stroke="{BORDER}"/>
  <rect x="24" y="18" width="12" height="12" rx="3" fill="{dot}"/>
  <text x="46" y="29" fill="{TEXT}" font-size="16" font-weight="700">{title}</text>
  <text x="{W-24}" y="29" fill="{MUTED}" font-size="11" text-anchor="end">{en}</text>
'''

FOOTER = "</svg>"


def save(name, svg):
    # 转义文本节点中的 & 为 &amp;（已为实体的不重复转义），保证 SVG XML 良构
    svg = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)", "&amp;", svg)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", name)


# ─────────────────────────────────────────────────────────
# 1. 测试规模与结果对比柱状图
# ─────────────────────────────────────────────────────────
def chart_test_results():
    s = header("测试规模与结果对比（2026-10-11 实跑）", "Test Results", GREEN)
    # 坐标区
    s += f'''  <line x1="100" y1="340" x2="640" y2="340" stroke="#334155" stroke-width="1.2"/>
  <line x1="100" y1="340" x2="100" y2="70" stroke="#334155" stroke-width="1.2"/>
  <g stroke="{BORDER}" stroke-width="1">
    <line x1="100" y1="285" x2="640" y2="285"/><line x1="100" y1="230" x2="640" y2="230"/>
    <line x1="100" y1="175" x2="640" y2="175"/><line x1="100" y1="120" x2="640" y2="120"/>
  </g>
  <g fill="{MUTED}" font-size="10" text-anchor="end">
    <text x="92" y="344">0</text><text x="92" y="289">75</text>
    <text x="92" y="234">150</text><text x="92" y="179">225</text>
    <text x="92" y="124">300</text>
  </g>
  <text x="62" y="205" fill="{SUB}" font-size="10.5" transform="rotate(-90 62 205)" text-anchor="middle">用例数（cases）</text>
'''
    # 数据：名称, 数值, 颜色, 浅色
    data = [
        ("后端集成", 341, BLUE, BLUE_LIGHT),
        ("前端组件", 142, GREEN, GREEN_LIGHT),
        ("拓扑封闭", 12, PURPLE, PURPLE_LIGHT),
        ("游客模式", 2, YELLOW, YELLOW_LIGHT),
        ("独立后台", 3, RED, "#FCA5A5"),
    ]
    base = 340
    maxv = 360
    x0 = 150
    for i, (name, v, c, cl) in enumerate(data):
        x = x0 + i * 100
        # 小数值柱按 22px 最小高度渲染（标签仍为真实值，避免 2/3 用例退化为一条线）
        h = max(v / maxv * 220, 22)
        y = base - h
        s += f'''    <rect x="{x}" y="{y}" width="72" height="{h}" rx="6" fill="{c}" opacity=".16"/>
    <rect x="{x}" y="{y}" width="72" height="{h}" rx="6" fill="none" stroke="{c}" stroke-width="1.4"/>
    <text x="{x+36}" y="{y-8}" fill="{cl}" font-size="15" font-weight="700" text-anchor="middle">{v}</text>
    <text x="{x+36}" y="{base+20}" fill="{LABEL}" font-size="12" font-weight="600" text-anchor="middle">{name}</text>
'''
    s += f'  <text x="150" y="385" fill="{MUTED}" font-size="9.5">注：拓扑封闭 12 / 游客模式 2 / 独立后台 3 的柱体按 ≥22px 最小高度渲染，柱顶标签为真实用例数</text>\n'
    # 右侧徽章
    s += f'''  <g text-anchor="middle">
    <rect x="680" y="80" width="240" height="64" rx="10" fill="#0F241C" stroke="{GREEN}"/>
    <text x="800" y="108" fill="{GREEN_LIGHT}" font-size="17" font-weight="700">483 项零失败</text>
    <text x="800" y="128" fill="{SUB}" font-size="10.5">341 后端 + 142 前端 · 0 失败</text>
    <rect x="680" y="158" width="240" height="64" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
    <text x="800" y="186" fill="{BLUE_LIGHT}" font-size="13" font-weight="600">后端 341 pass / 1 skip / 2 xfail</text>
    <text x="800" y="206" fill="{MUTED}" font-size="10.5">skip=需真实LLM · xfail=SISA迁移管线</text>
    <rect x="680" y="236" width="240" height="64" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
    <text x="800" y="264" fill="{GREEN_LIGHT}" font-size="13" font-weight="600">前端 142 / 142 全通过</text>
    <text x="800" y="284" fill="{MUTED}" font-size="10.5">10 测试文件（4 spec + 6 test）</text>
  </g>
'''
    save("october-test-results.svg", s + FOOTER)


# ─────────────────────────────────────────────────────────
# 2. 后端回归结果环形图
# ─────────────────────────────────────────────────────────
def chart_regression_donut():
    s = header("后端回归结果构成（344 用例）", "Backend Regression", BLUE)
    cx, cy, r, r_hole = 230, 230, 110, 66
    segs = [
        ("通过 (pass)", 341, GREEN),
        ("跳过 (skip)", 1, BLUE),
        ("预期失败 (xfail)", 2, YELLOW),
    ]
    total = sum(v for _, v, _ in segs)
    # 小占比扇区（1 用例=1.05°、2 用例=2.09°）按 ≥4° 最小角度放大显示，
    # 差额从最大扇区（pass）扣；精确占比以图例数字为准
    raw = [v / total * 2 * math.pi for _, v, _ in segs]
    min_ang = math.radians(4)
    angles = [max(a, min_ang) for a in raw]
    angles[raw.index(max(raw))] -= sum(angles) - 2 * math.pi
    start = -math.pi / 2
    for (name, v, c), ang in zip(segs, angles):
        end = start + ang
        x1 = cx + r * math.cos(start)
        y1 = cy + r * math.sin(start)
        x2 = cx + r * math.cos(end)
        y2 = cy + r * math.sin(end)
        xh1 = cx + r_hole * math.cos(end)
        yh1 = cy + r_hole * math.sin(end)
        xh2 = cx + r_hole * math.cos(start)
        yh2 = cy + r_hole * math.sin(start)
        large = 1 if ang > math.pi else 0
        d = f"M{x1} {y1} A{r} {r} 0 {large} 1 {x2} {y2} L{xh1} {yh1} A{r_hole} {r_hole} 0 {large} 0 {xh2} {yh2} Z"
        s += f'  <path d="{d}" fill="{c}" opacity=".85"/>\n'
        start = end
    s += f'  <text x="{cx}" y="{cy-2}" fill="{TEXT}" font-size="26" font-weight="700" text-anchor="middle">344</text>\n'
    s += f'  <text x="{cx}" y="{cy+20}" fill="{SUB}" font-size="11" text-anchor="middle">总用例</text>\n'
    # 图例
    lx, ly = 420, 130
    for name, v, c in segs:
        pct = v / total * 100
        s += f'''  <rect x="{lx}" y="{ly}" width="14" height="14" rx="3" fill="{c}"/>
  <text x="{lx+22}" y="{ly+11}" fill="{LABEL}" font-size="12.5" font-weight="600">{name}</text>
  <text x="{lx+22}" y="{ly+28}" fill="{MUTED}" font-size="10.5">{v} 用例 · {pct:.2f}%</text>
'''
        ly += 54
    s += f'  <text x="420" y="306" fill="{MUTED}" font-size="9.5">注：skip / xfail 扇区按 ≥4° 最小角度放大显示，精确占比以图例数字为准</text>\n'
    s += f'''  <rect x="420" y="330" width="480" height="64" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
  <text x="440" y="356" fill="{GREEN_LIGHT}" font-size="12.5" font-weight="600">结论：零非预期失败</text>
  <text x="440" y="378" fill="{SUB}" font-size="10.5">1 skip 需真实 SiliconFlow（RUN_REAL_LLM=1）；2 xfail 为已迁 SISA 的曲率管线，标注不再适用</text>
'''
    save("october-regression-donut.svg", s + FOOTER)


# ─────────────────────────────────────────────────────────
# 3. 新增/改写测试条形图
# ─────────────────────────────────────────────────────────
def chart_new_tests():
    s = header("本轮新增 / 改写测试用例分布", "New & Rewritten Tests", PURPLE)
    data = [
        ("test_car_topology_closure.py", 12, PURPLE, PURPLE_LIGHT, "新增：整车7类开口封闭"),
        ("authStore.spec.js", 13, GREEN, GREEN_LIGHT, "改写：游客态语义"),
        ("routerGuard.spec.js", 5, BLUE, BLUE_LIGHT, "改写：移除 Admin/Login 路由"),
        ("test_admin_console.py", 3, RED, "#FCA5A5", "新增：后台托管+CSP边界"),
        ("test_guest_mode.py", 2, YELLOW, YELLOW_LIGHT, "新增：游客放行+生产fail-fast"),
    ]
    y0 = 76
    bar_h = 34
    gap = 14
    label_x = 300          # 文件名右对齐边界
    bar_x = 316            # 条轨起点
    track_w = 300          # 条轨宽度（与右侧注释列分离，杜绝文字压条）
    note_x = bar_x + track_w + 16
    maxv = 15
    for i, (name, v, c, cl, note) in enumerate(data):
        y = y0 + i * (bar_h + gap)
        w = v / maxv * track_w
        s += f'''  <text x="{label_x}" y="{y+21}" fill="{LABEL}" font-size="10.5" text-anchor="end" font-family="Consolas,monospace">{name}</text>
  <rect x="{bar_x}" y="{y}" width="{track_w}" height="{bar_h}" rx="6" fill="{PANEL}" stroke="{BORDER}"/>
  <rect x="{bar_x}" y="{y}" width="{w}" height="{bar_h}" rx="6" fill="{c}" opacity=".2"/>
  <rect x="{bar_x}" y="{y}" width="{w}" height="{bar_h}" rx="6" fill="none" stroke="{c}" stroke-width="1.4"/>
  <text x="{bar_x+10}" y="{y+22}" fill="{cl}" font-size="13" font-weight="700">{v}</text>
  <text x="{note_x}" y="{y+21}" fill="{MUTED}" font-size="9.5">{note}</text>
'''
    s += f'''  <text x="{bar_x}" y="320" fill="{SUB}" font-size="10.5">合计 {sum(v for _,v,_,_,_ in data)} 用例 · 覆盖拓扑封闭 / 游客模式 / 后台托管 / 路由守卫 / 身份状态</text>
  <rect x="{bar_x}" y="334" width="460" height="58" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
  <text x="{bar_x+16}" y="360" fill="{GREEN_LIGHT}" font-size="12" font-weight="600">回归结论：483 项（341+142）零失败 · 历史用例无回退</text>
  <text x="{bar_x+16}" y="381" fill="{MUTED}" font-size="10">pytest 强制 GUEST_MODE=false，防止 401/403 语义用例被游客旁路击穿</text>
'''
    save("october-new-tests.svg", s + FOOTER)


# ─────────────────────────────────────────────────────────
# 4. Admin 模块后移流程图
# ─────────────────────────────────────────────────────────
def chart_admin_flow():
    s = header("Admin 模块后移：公开前端 → 后端独立托管", "Admin Relocation Flow", RED)
    def arrow(x1, y1, x2, y2, c=BLUE):
        return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="1.6" marker-end="url(#a)"/>\n'
    s += '''  <defs>
    <marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0L10 5L0 10z" fill="#38BDF8"/>
    </marker>
  </defs>
'''
    # 左：旧状态
    s += f'''  <rect x="40" y="80" width="200" height="90" rx="10" fill="#2A0F1A" stroke="{RED}"/>
  <text x="140" y="112" fill="{RED}" font-size="13" font-weight="700" text-anchor="middle">❌ 旧：公开前端</text>
  <text x="140" y="134" fill="{SUB}" font-size="10.5" text-anchor="middle">主站 SPA 内置 /admin 路由</text>
  <text x="140" y="152" fill="{MUTED}" font-size="10" text-anchor="middle">Admin 代码随 gh-pages 公开下载</text>
'''
    # 右：新状态
    s += f'''  <rect x="40" y="250" width="200" height="90" rx="10" fill="#0F241C" stroke="{GREEN}"/>
  <text x="140" y="282" fill="{GREEN_LIGHT}" font-size="13" font-weight="700" text-anchor="middle">✅ 新：后端独立托管</text>
  <text x="140" y="304" fill="{SUB}" font-size="10.5" text-anchor="middle">FastAPI StaticFiles /admin</text>
  <text x="140" y="322" fill="{MUTED}" font-size="10" text-anchor="middle">公开站零 Admin 代码</text>
'''
    s += arrow(140, 170, 140, 250)
    # 中间步骤
    steps = [
        ("主站移除", "/admin 路由\n+ 侧栏管理分组\n+ Admin chunk", BLUE, BLUE_LIGHT),
        ("独立构建", "admin.html\nadmin_main.js\nAdminGate 登录门", PURPLE, PURPLE_LIGHT),
        ("后端托管", "vite.admin.config.js\n→ static/admin\nFastAPI mount /admin", GREEN, GREEN_LIGHT),
        ("CSP 作用域", "/admin 文档专用\nunsafe-eval 放行\n公开站保持严格", YELLOW, YELLOW_LIGHT),
    ]
    for i, (t, body, c, cl) in enumerate(steps):
        x = 300 + i * 155
        s += f'''  <rect x="{x}" y="120" width="140" height="110" rx="10" fill="{PANEL}" stroke="{c}"/>
  <circle cx="{x+70}" cy="110" r="11" fill="{c}"/>
  <text x="{x+70}" y="114" fill="{BG}" font-size="11" font-weight="700" text-anchor="middle">{i+1}</text>
  <text x="{x+70}" y="148" fill="{cl}" font-size="12" font-weight="700" text-anchor="middle">{t}</text>
'''
        for j, line in enumerate(body.split("\n")):
            s += f'  <text x="{x+70}" y="{172+j*16}" fill="{SUB}" font-size="10" text-anchor="middle">{line}</text>\n'
        if i < 3:
            s += arrow(x + 140, 175, x + 155, 175)
    # 登录门语义（三点单列排布，避免长文本右溢出 viewBox）
    s += f'''  <rect x="320" y="268" width="580" height="102" rx="10" fill="{PANEL}" stroke="{PURPLE}"/>
  <text x="340" y="294" fill="{PURPLE_LIGHT}" font-size="12.5" font-weight="700">登录门语义</text>
  <g font-size="10.5" fill="{SUB}">
    <circle cx="340" cy="316" r="2.5" fill="{GREEN}"/><text x="350" y="320">游客模式：自动进入（guest/superadmin）</text>
    <circle cx="340" cy="338" r="2.5" fill="{BLUE}"/><text x="350" y="342">生产环境：管理员邮箱口令登录，非管理员显示无权限</text>
    <circle cx="340" cy="360" r="2.5" fill="{YELLOW}"/><text x="350" y="364">5 标签完整保留：登录记录 / 用户管理 / 后端错误 / 审计日志 / 影响证据</text>
  </g>
'''
    save("october-admin-flow.svg", s + FOOTER)


# ─────────────────────────────────────────────────────────
# 5. 游客模式架构图
# ─────────────────────────────────────────────────────────
def chart_guest_arch():
    s = header("游客模式架构：全功能开放 + 生产防护", "Guest Mode Architecture", YELLOW)
    # 访客（节点链整体上移至垂直居中，消除顶部大面积留白）
    s += f'''  <rect x="40" y="150" width="120" height="70" rx="10" fill="{PANEL}" stroke="{MUTED}"/>
  <text x="100" y="182" fill="{TEXT}" font-size="13" font-weight="700" text-anchor="middle">匿名访客</text>
  <text x="100" y="202" fill="{SUB}" font-size="10" text-anchor="middle">无令牌访问</text>
'''
    # 旁路判定
    s += f'''  <rect x="220" y="140" width="160" height="90" rx="10" fill="#1A1230" stroke="{PURPLE}"/>
  <text x="300" y="170" fill="{PURPLE_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">GUEST_MODE 开关</text>
  <text x="300" y="192" fill="{SUB}" font-size="10" text-anchor="middle">get_current_user 旁路</text>
  <text x="300" y="210" fill="{MUTED}" font-size="9.5" text-anchor="middle">security.py</text>
'''
    # 内置 guest
    s += f'''  <rect x="440" y="140" width="180" height="90" rx="10" fill="#0F241C" stroke="{GREEN}"/>
  <text x="530" y="170" fill="{GREEN_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">内置 guest 账户</text>
  <text x="530" y="192" fill="{SUB}" font-size="10" text-anchor="middle">guest@evolution-ai.design</text>
  <text x="530" y="210" fill="{MUTED}" font-size="9.5" text-anchor="middle">role=superadmin · 惰性幂等创建</text>
'''
    # 全功能
    s += f'''  <rect x="680" y="130" width="240" height="110" rx="10" fill="{PANEL}" stroke="{BLUE}"/>
  <text x="800" y="160" fill="{BLUE_LIGHT}" font-size="12.5" font-weight="700" text-anchor="middle">全功能可达</text>
  <g font-size="10" fill="{SUB}">
    <text x="700" y="184">• Designer / Projects / Quality</text>
    <text x="700" y="202">• Deliver / DEMO / Community</text>
    <text x="700" y="220">• /admin 后台（游客为 superadmin）</text>
  </g>
'''
    def arrow(x1, y1, x2, y2, c=BLUE):
        return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="1.6" marker-end="url(#g)"/>\n'
    s += '''  <defs><marker id="g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#38BDF8"/></marker></defs>
'''
    s += arrow(160, 185, 220, 185) + arrow(380, 185, 440, 185) + arrow(620, 185, 680, 185)

    # 生产防护
    s += f'''  <rect x="40" y="272" width="880" height="84" rx="10" fill="#2A1212" stroke="{RED}"/>
  <text x="60" y="300" fill="{RED}" font-size="12.5" font-weight="700">生产环境防护（fail-fast）</text>
  <g font-size="10.5" fill="{SUB}">
    <circle cx="60" cy="322" r="2.5" fill="{RED}"/><text x="72" y="326">ENVIRONMENT=production 且 GUEST_MODE=true → 启动直接拒绝（与弱 SECRET_KEY 同级校验）</text>
    <circle cx="60" cy="344" r="2.5" fill="{YELLOW}"/><text x="72" y="348">测试套件强制 GUEST_MODE=false（conftest），防止 401/403 语义用例被游客旁路击穿</text>
  </g>
'''
    save("october-guest-arch.svg", s + FOOTER)


# ─────────────────────────────────────────────────────────
# 6. 8 提交时间线
# ─────────────────────────────────────────────────────────
def chart_timeline():
    s = header("10 月迭代时间线（合入 main 的 8 个提交）", "Iteration Timeline", BLUE)
    commits = [
        ("ea41ce3b", "10-10", "NURBS 连续车身几何重构", "第二阶段 + 渲染修复", GREEN),
        ("6df66e06", "10-10", "车漆反光调优", "轮眉渐隐消除台阶", GREEN),
        ("4ab70371", "10-10", "整车封闭化", "7 类开口全部封闭", GREEN),
        ("7c128f4c", "10-10", "流线型造型", "俯视收窄+斜背圆角", GREEN),
        ("6040bac4", "10-11", "账号体系封存", "全功能游客模式+Contact", YELLOW),
        ("a40226e6", "10-11", "京东云部署清单", "2C4G 一键部署+初始化", BLUE),
        ("c45d9ccc", "10-11", "Admin 模块后移", "/admin 独立托管+登录门", RED),
        ("864421d5", "10-11", "CSP 作用域修复", "unsafe-eval 仅 /admin 放行", RED),
    ]
    n = len(commits)
    y_line = 230
    x_start, x_end = 80, 880
    step = (x_end - x_start) / (n - 1)
    s += f'  <line x1="{x_start}" y1="{y_line}" x2="{x_end}" y2="{y_line}" stroke="#334155" stroke-width="2"/>\n'
    for i, (h, date, title, sub, c) in enumerate(commits):
        x = x_start + i * step
        # 日期标签
        s += f'  <text x="{x}" y="{y_line-14}" fill="{MUTED}" font-size="10" text-anchor="middle">{date}</text>\n'
        s += f'  <circle cx="{x}" cy="{y_line}" r="7" fill="{BG}" stroke="{c}" stroke-width="2.4"/>\n'
        s += f'  <circle cx="{x}" cy="{y_line}" r="3" fill="{c}"/>\n'
        # 上下交替
        if i % 2 == 0:
            by = y_line + 30
            s += f'  <rect x="{x-72}" y="{by}" width="144" height="62" rx="8" fill="{PANEL}" stroke="{c}"/>\n'
            s += f'  <text x="{x}" y="{by+20}" fill="{TEXT}" font-size="11" font-weight="700" text-anchor="middle">{title}</text>\n'
            s += f'  <text x="{x}" y="{by+40}" fill="{SUB}" font-size="9.5" text-anchor="middle">{sub}</text>\n'
            s += f'  <text x="{x}" y="{by+55}" fill="{MUTED}" font-size="8.5" text-anchor="middle" font-family="Consolas,monospace">{h}</text>\n'
        else:
            by = y_line - 96
            s += f'  <rect x="{x-72}" y="{by}" width="144" height="62" rx="8" fill="{PANEL}" stroke="{c}"/>\n'
            s += f'  <text x="{x}" y="{by+20}" fill="{TEXT}" font-size="11" font-weight="700" text-anchor="middle">{title}</text>\n'
            s += f'  <text x="{x}" y="{by+40}" fill="{SUB}" font-size="9.5" text-anchor="middle">{sub}</text>\n'
            s += f'  <text x="{x}" y="{by+55}" fill="{MUTED}" font-size="8.5" text-anchor="middle" font-family="Consolas,monospace">{h}</text>\n'
    s += f'''  <rect x="80" y="350" width="800" height="50" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
  <text x="100" y="374" fill="{GREEN_LIGHT}" font-size="11.5" font-weight="600">主线 HEAD: 864421d5 （feature 分支快进合入 main）</text>
  <text x="100" y="392" fill="{MUTED}" font-size="10">前 4 提交=NURBS 封闭化·造型 · 中间 2 提交=账号封存·部署 · 后 2 提交=Admin 后移·CSP 修复</text>
'''
    save("october-timeline.svg", s + FOOTER)


# ─────────────────────────────────────────────────────────
# 7. 7 类开口封闭分类
# ─────────────────────────────────────────────────────────
def chart_closure():
    s = header("整车 7 类开口封闭（拓扑对齐规范）", "Body Opening Closure", GREEN)
    cats = [
        ("前脸中央封板", "前保与机舱之间", GREEN),
        ("尾门封板", "尾门开口封闭", GREEN),
        ("A/C 柱三角楔", "柱与玻璃共边", PURPLE),
        ("cowl 封条", "机盖→风挡过渡", BLUE),
        ("底盘托盘", "底部全封闭", BLUE),
        ("轮拱内衬", "轮拱开口内衬", YELLOW),
        ("内饰搁板", "防透视封堵", RED),
    ]
    cols = 4
    cell_w, cell_h = 200, 110
    x0, y0 = 70, 80
    for i, (name, desc, c) in enumerate(cats):
        col = i % cols
        row = i // cols
        x = x0 + col * (cell_w + 20)
        y = y0 + row * (cell_h + 24)
        s += f'''  <rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="10" fill="{PANEL}" stroke="{c}"/>
  <circle cx="{x+24}" cy="{y+30}" r="10" fill="{c}" opacity=".25"/>
  <circle cx="{x+24}" cy="{y+30}" r="5" fill="{c}"/>
  <text x="{x+44}" y="{y+35}" fill="{TEXT}" font-size="13" font-weight="700">{name}</text>
  <text x="{x+20}" y="{y+66}" fill="{SUB}" font-size="10.5">{desc}</text>
  <text x="{x+20}" y="{y+88}" fill="{MUTED}" font-size="9.5">尺寸·装配·拓扑对齐规范</text>
'''
    s += f'''  <rect x="70" y="330" width="820" height="70" rx="10" fill="#0F241C" stroke="{GREEN}"/>
  <text x="90" y="358" fill="{GREEN_LIGHT}" font-size="12.5" font-weight="700">验证：test_car_topology_closure.py · 12/12 全通过</text>
  <text x="90" y="380" fill="{SUB}" font-size="10.5">覆盖横链边重合、cowl 封条、柱楔共边、底盘封闭、前后封板、俯视收窄、门框压条、轮拱内衬、防透视搁板、零件普查</text>
'''
    save("october-closure.svg", s + FOOTER)


# ─────────────────────────────────────────────────────────
# 8. 部署拓扑图
# ─────────────────────────────────────────────────────────
def chart_deployment():
    s = header("生产部署拓扑（内地合规 + 同域反代）", "Deployment Topology", BLUE)
    # 浏览器
    s += f'''  <rect x="40" y="190" width="110" height="60" rx="10" fill="{PANEL}" stroke="{MUTED}"/>
  <text x="95" y="218" fill="{TEXT}" font-size="12" font-weight="700" text-anchor="middle">浏览器</text>
  <text x="95" y="236" fill="{SUB}" font-size="10" text-anchor="middle">用户端</text>
'''
    # Nginx
    s += f'''  <rect x="210" y="170" width="150" height="100" rx="10" fill="#0B1A2E" stroke="{BLUE}"/>
  <text x="285" y="200" fill="{BLUE_LIGHT}" font-size="12.5" font-weight="700" text-anchor="middle">Nginx (TLS)</text>
  <text x="285" y="222" fill="{SUB}" font-size="10" text-anchor="middle">同域反代</text>
  <text x="285" y="240" fill="{MUTED}" font-size="9.5" text-anchor="middle">/ → dist 静态</text>
  <text x="285" y="256" fill="{MUTED}" font-size="9.5" text-anchor="middle">/api & /admin → 后端</text>
'''
    # 静态站
    s += f'''  <rect x="420" y="70" width="180" height="70" rx="10" fill="{PANEL}" stroke="{GREEN}"/>
  <text x="510" y="100" fill="{GREEN_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">GitHub Pages / dist</text>
  <text x="510" y="120" fill="{SUB}" font-size="10" text-anchor="middle">公开静态站（零 Admin 代码）</text>
'''
    # 后端
    s += f'''  <rect x="420" y="170" width="180" height="100" rx="10" fill="#0F241C" stroke="{PURPLE}"/>
  <text x="510" y="200" fill="{PURPLE_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">FastAPI 后端</text>
  <text x="510" y="220" fill="{SUB}" font-size="10" text-anchor="middle">/api/v1/* 业务接口</text>
  <text x="510" y="238" fill="{SUB}" font-size="10" text-anchor="middle">/admin 独立后台</text>
  <text x="510" y="256" fill="{MUTED}" font-size="9.5" text-anchor="middle">GUEST_MODE（封存期）</text>
'''
    # 数据层
    s += f'''  <rect x="420" y="290" width="180" height="70" rx="10" fill="{PANEL}" stroke="{YELLOW}"/>
  <text x="510" y="320" fill="{YELLOW_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">PostgreSQL + Redis</text>
  <text x="510" y="340" fill="{SUB}" font-size="10" text-anchor="middle">数据 + 会话/限流</text>
'''
    # 京东云
    s += f'''  <rect x="680" y="150" width="220" height="130" rx="10" fill="#1A1230" stroke="{PURPLE}" stroke-dasharray="4 3"/>
  <text x="790" y="178" fill="{PURPLE_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">京东云 2C4G（内地合规）</text>
  <text x="790" y="198" fill="{SUB}" font-size="10" text-anchor="middle">2G swap · Docker 四服务栈</text>
  <text x="790" y="216" fill="{SUB}" font-size="10" text-anchor="middle">域名转入境内 + ICP 备案</text>
  <text x="790" y="234" fill="{MUTED}" font-size="9.5" text-anchor="middle">含微信扫码须内地服务器</text>
  <text x="790" y="256" fill="{YELLOW_LIGHT}" font-size="9.5" text-anchor="middle">PIPL 数据不出境</text>
'''
    def arrow(x1, y1, x2, y2, c=BLUE):
        return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="1.6" marker-end="url(#d)"/>\n'
    s += '''  <defs><marker id="d" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#38BDF8"/></marker></defs>
'''
    s += arrow(150, 220, 210, 220)
    s += arrow(360, 180, 420, 105, GREEN)   # → Pages
    s += arrow(360, 220, 420, 220, PURPLE)  # → backend
    s += arrow(510, 270, 510, 290, YELLOW)  # → db
    s += f'  <line x1="600" y1="220" x2="680" y2="220" stroke="{PURPLE}" stroke-width="1.6" stroke-dasharray="4 3"/>\n'
    s += f'  <text x="640" y="212" fill="{MUTED}" font-size="9" text-anchor="middle">部署承载</text>'
    save("october-deployment.svg", s + FOOTER)


# ─────────────────────────────────────────────────────────
# 9. CSP 作用域关系图
# ─────────────────────────────────────────────────────────
def chart_csp_scope():
    s = header("CSP 作用域：/admin 放行 unsafe-eval · 其余严格", "CSP Scoping", YELLOW)
    # 全局严格
    s += f'''  <rect x="60" y="80" width="380" height="130" rx="12" fill="{PANEL}" stroke="{GREEN}"/>
  <text x="250" y="110" fill="{GREEN_LIGHT}" font-size="13" font-weight="700" text-anchor="middle">公开 API + 主站（默认严格）</text>
  <text x="250" y="134" fill="{LABEL}" font-size="11" text-anchor="middle" font-family="Consolas,monospace">script-src 'self'</text>
  <text x="250" y="154" fill="{MUTED}" font-size="10" text-anchor="middle">无 unsafe-eval · 拦截 vue-i18n Function 构造器</text>
  <text x="250" y="176" fill="{SUB}" font-size="10.5" text-anchor="middle">/api/v1/* · evolution-ai.design 首页</text>
'''
    # /admin 作用域
    s += f'''  <rect x="520" y="80" width="380" height="130" rx="12" fill="#1A1230" stroke="{PURPLE}"/>
  <text x="710" y="110" fill="{PURPLE_LIGHT}" font-size="13" font-weight="700" text-anchor="middle">/admin 文档（专用放宽）</text>
  <text x="710" y="134" fill="{LABEL}" font-size="11" text-anchor="middle" font-family="Consolas,monospace">script-src 'self' 'unsafe-eval'</text>
  <text x="710" y="154" fill="{MUTED}" font-size="10" text-anchor="middle">仅允许 Function 构造器供 vue-i18n 编译</text>
  <text x="710" y="176" fill="{SUB}" font-size="10.5" text-anchor="middle">/admin/ · /admin/assets/*</text>
'''
    # 中间判定
    s += f'''  <rect x="380" y="240" width="200" height="70" rx="10" fill="#0B101A" stroke="{BLUE}"/>
  <text x="480" y="268" fill="{BLUE_LIGHT}" font-size="11.5" font-weight="700" text-anchor="middle">SecurityHeadersMiddleware</text>
  <text x="480" y="288" fill="{SUB}" font-size="10" text-anchor="middle">按请求路径选择 CSP 策略</text>
'''
    s += '''  <defs><marker id="c" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#38BDF8"/></marker></defs>
'''
    s += f'  <line x1="250" y1="210" x2="420" y2="240" stroke="{GREEN}" stroke-width="1.6" marker-end="url(#c)"/>\n'
    s += f'  <line x1="710" y1="210" x2="540" y2="240" stroke="{PURPLE}" stroke-width="1.6" marker-end="url(#c)"/>\n'
    # 缺陷→修复
    s += f'''  <rect x="60" y="330" width="840" height="70" rx="10" fill="#2A1212" stroke="{RED}"/>
  <text x="80" y="356" fill="{RED}" font-size="11.5" font-weight="700">缺陷与修复</text>
  <g font-size="10.5" fill="{SUB}">
    <circle cx="80" cy="378" r="2.5" fill="{RED}"/><text x="92" y="382">首测后台白屏：EvalError - 'unsafe-eval' is not an allowed source of script</text>
    <circle cx="500" cy="378" r="2.5" fill="{GREEN}"/><text x="512" y="382">修复：/admin 文档作用域单独放行 unsafe-eval；回归测试锁定边界（test_admin_console.py）</text>
  </g>
'''
    save("october-csp-scope.svg", s + FOOTER)


if __name__ == "__main__":
    chart_test_results()
    chart_regression_donut()
    chart_new_tests()
    chart_admin_flow()
    chart_guest_arch()
    chart_timeline()
    chart_closure()
    chart_deployment()
    chart_csp_scope()
    print("done")
