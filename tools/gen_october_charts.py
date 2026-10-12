"""生成 10 月审计/测试报告的标准化可视化图表（SVG，零依赖，GitHub Pages 兼容）。
设计系统继承 docs/images/ 已有图表：深色主题 + 四色强调。
双语同产：zh → docs/images/，en → docs/images/en/（文件名相同、<text> 数量相等）。
运行: python tools/gen_october_charts.py
"""
import math
import os
import re
from xml.sax.saxutils import escape as _esc

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "images")
EN_OUT = os.path.join(OUT, "en")
os.makedirs(OUT, exist_ok=True)
os.makedirs(EN_OUT, exist_ok=True)

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


def save(name, svg, lang="zh"):
    # 转义文本节点中的 & 为 &amp;（已为实体的不重复转义），保证 SVG XML 良构
    svg = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)", "&amp;", svg)
    out_dir = OUT if lang == "zh" else EN_OUT
    p = os.path.join(out_dir, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", lang, name)


# ─────────────────────────────────────────────────────────
# 1. 测试规模与结果对比柱状图
# ─────────────────────────────────────────────────────────
def chart_test_results(lang="zh"):
    T = {
        "zh": dict(
            title="测试规模与结果对比（2026-10-11 实跑）", yaxis="用例数（cases）",
            names=["后端集成", "前端组件", "拓扑封闭", "游客模式", "独立后台"],
            note="注：拓扑封闭 12 / 游客模式 2 / 独立后台 3 的柱体按 ≥22px 最小高度渲染，柱顶标签为真实用例数",
            b1=("483 项零失败", "341 后端 + 142 前端 · 0 失败"),
            b2=("后端 341 pass / 1 skip / 2 xfail", "skip=需真实LLM · xfail=SISA迁移管线"),
            b3=("前端 142 / 142 全通过", "10 测试文件（4 spec + 6 test）"),
        ),
        "en": dict(
            title="Test scale vs results (run 2026-10-11)", yaxis="Cases",
            names=["Backend", "Frontend", "Topology", "Guest", "Admin"],
            note="Note: Topology 12 / Guest 2 / Admin 3 bars rendered at ≥22px min height; top labels show real case counts",
            b1=("483 cases, 0 failures", "341 backend + 142 frontend · 0 failed"),
            b2=("Backend 341 pass / 1 skip / 2 xfail", "skip=needs real LLM · xfail=SISA-migrated pipeline"),
            b3=("Frontend 142 / 142 all pass", "10 test files (4 spec + 6 test)"),
        ),
    }[lang]
    s = header(T["title"], "Test Results", GREEN)
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
  <text x="62" y="205" fill="{SUB}" font-size="10.5" transform="rotate(-90 62 205)" text-anchor="middle">{T["yaxis"]}</text>
'''
    # 数据：数值, 颜色, 浅色（名称按语言取）
    data = [
        (341, BLUE, BLUE_LIGHT),
        (142, GREEN, GREEN_LIGHT),
        (12, PURPLE, PURPLE_LIGHT),
        (2, YELLOW, YELLOW_LIGHT),
        (3, RED, "#FCA5A5"),
    ]
    base = 340
    maxv = 360
    x0 = 150
    for i, (v, c, cl) in enumerate(data):
        name = T["names"][i]
        x = x0 + i * 100
        # 小数值柱按 22px 最小高度渲染（标签仍为真实值，避免 2/3 用例退化为一条线）
        h = max(v / maxv * 220, 22)
        y = base - h
        s += f'''    <rect x="{x}" y="{y}" width="72" height="{h}" rx="6" fill="{c}" opacity=".16"/>
    <rect x="{x}" y="{y}" width="72" height="{h}" rx="6" fill="none" stroke="{c}" stroke-width="1.4"/>
    <text x="{x+36}" y="{y-8}" fill="{cl}" font-size="15" font-weight="700" text-anchor="middle">{v}</text>
    <text x="{x+36}" y="{base+20}" fill="{LABEL}" font-size="12" font-weight="600" text-anchor="middle">{name}</text>
'''
    s += f'  <text x="150" y="385" fill="{MUTED}" font-size="9.5">{T["note"]}</text>\n'
    # 右侧徽章
    s += f'''  <g text-anchor="middle">
    <rect x="680" y="80" width="240" height="64" rx="10" fill="#0F241C" stroke="{GREEN}"/>
    <text x="800" y="108" fill="{GREEN_LIGHT}" font-size="17" font-weight="700">{T["b1"][0]}</text>
    <text x="800" y="128" fill="{SUB}" font-size="10.5">{T["b1"][1]}</text>
    <rect x="680" y="158" width="240" height="64" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
    <text x="800" y="186" fill="{BLUE_LIGHT}" font-size="13" font-weight="600">{T["b2"][0]}</text>
    <text x="800" y="206" fill="{MUTED}" font-size="10">{T["b2"][1]}</text>
    <rect x="680" y="236" width="240" height="64" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
    <text x="800" y="264" fill="{GREEN_LIGHT}" font-size="13" font-weight="600">{T["b3"][0]}</text>
    <text x="800" y="284" fill="{MUTED}" font-size="10.5">{T["b3"][1]}</text>
  </g>
'''
    save("october-test-results.svg", s + FOOTER, lang)


# ─────────────────────────────────────────────────────────
# 2. 后端回归结果环形图
# ─────────────────────────────────────────────────────────
def chart_regression_donut(lang="zh"):
    T = {
        "zh": dict(
            title="后端回归结果构成（344 用例）",
            segs=["通过 (pass)", "跳过 (skip)", "预期失败 (xfail)"],
            total="总用例", unit="{v} 用例 · {pct:.2f}%",
            note="注：skip / xfail 扇区按 ≥4° 最小角度放大显示，精确占比以图例数字为准",
            concl="结论：零非预期失败",
            detail="1 skip 需真实 SiliconFlow（RUN_REAL_LLM=1）；2 xfail 为已迁 SISA 的曲率管线，标注不再适用",
            detail_size="10.5",
        ),
        "en": dict(
            title="Backend regression breakdown (344 cases)",
            segs=["Pass", "Skip", "Expected fail (xfail)"],
            total="Total", unit="{v} cases · {pct:.2f}%",
            note="Note: skip / xfail slices enlarged to ≥4° min angle; exact ratios per legend numbers",
            concl="Conclusion: zero unexpected failures",
            detail="1 skip needs real SiliconFlow (RUN_REAL_LLM=1); 2 xfail are curvature pipelines migrated to SISA, marked N/A",
            detail_size="10",
        ),
    }[lang]
    s = header(T["title"], "Backend Regression", BLUE)
    cx, cy, r, r_hole = 230, 230, 110, 66
    segs = [
        (T["segs"][0], 341, GREEN),
        (T["segs"][1], 1, BLUE),
        (T["segs"][2], 2, YELLOW),
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
    s += f'  <text x="{cx}" y="{cy+20}" fill="{SUB}" font-size="11" text-anchor="middle">{T["total"]}</text>\n'
    # 图例
    lx, ly = 420, 130
    for name, v, c in segs:
        pct = v / total * 100
        s += f'''  <rect x="{lx}" y="{ly}" width="14" height="14" rx="3" fill="{c}"/>
  <text x="{lx+22}" y="{ly+11}" fill="{LABEL}" font-size="12.5" font-weight="600">{name}</text>
  <text x="{lx+22}" y="{ly+28}" fill="{MUTED}" font-size="10.5">{T["unit"].format(v=v, pct=pct)}</text>
'''
        ly += 54
    s += f'  <text x="420" y="306" fill="{MUTED}" font-size="9.5">{T["note"]}</text>\n'
    s += f'''  <rect x="420" y="330" width="480" height="64" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
  <text x="440" y="356" fill="{GREEN_LIGHT}" font-size="12.5" font-weight="600">{T["concl"]}</text>
  <text x="440" y="378" fill="{SUB}" font-size="{T["detail_size"]}">{T["detail"]}</text>
'''
    save("october-regression-donut.svg", s + FOOTER, lang)


# ─────────────────────────────────────────────────────────
# 3. 新增/改写测试条形图
# ─────────────────────────────────────────────────────────
def chart_new_tests(lang="zh"):
    T = {
        "zh": dict(
            title="本轮新增 / 改写测试用例分布",
            notes=["新增：整车7类开口封闭", "改写：游客态语义", "改写：移除 Admin/Login 路由",
                   "新增：后台托管+CSP边界", "新增：游客放行+生产fail-fast"],
            total="合计 35 用例 · 覆盖拓扑封闭 / 游客模式 / 后台托管 / 路由守卫 / 身份状态",
            concl="回归结论：483 项（341+142）零失败 · 历史用例无回退",
            guard="pytest 强制 GUEST_MODE=false，防止 401/403 语义用例被游客旁路击穿",
        ),
        "en": dict(
            title="New / rewritten test cases this round",
            notes=["New: 7 body openings sealed", "Rewrite: guest-state semantics",
                   "Rewrite: Admin/Login routes removed", "New: admin hosting + CSP boundary",
                   "New: guest pass + prod fail-fast"],
            total="Total 35 cases · topology closure / guest mode / admin hosting / router guard / auth state",
            concl="Regression: 483 cases (341+142) zero failures · no historical regressions",
            guard="pytest enforces GUEST_MODE=false so 401/403 semantic cases are not guest-bypassed",
        ),
    }[lang]
    s = header(T["title"], "New & Rewritten Tests", PURPLE)
    data = [
        ("test_car_topology_closure.py", 12, PURPLE, PURPLE_LIGHT),
        ("authStore.spec.js", 13, GREEN, GREEN_LIGHT),
        ("routerGuard.spec.js", 5, BLUE, BLUE_LIGHT),
        ("test_admin_console.py", 3, RED, "#FCA5A5"),
        ("test_guest_mode.py", 2, YELLOW, YELLOW_LIGHT),
    ]
    y0 = 76
    bar_h = 34
    gap = 14
    label_x = 300          # 文件名右对齐边界
    bar_x = 316            # 条轨起点
    track_w = 300          # 条轨宽度（与右侧注释列分离，杜绝文字压条）
    note_x = bar_x + track_w + 16
    maxv = 15
    for i, (name, v, c, cl) in enumerate(data):
        note = T["notes"][i]
        y = y0 + i * (bar_h + gap)
        w = v / maxv * track_w
        s += f'''  <text x="{label_x}" y="{y+21}" fill="{LABEL}" font-size="10.5" text-anchor="end" font-family="Consolas,monospace">{name}</text>
  <rect x="{bar_x}" y="{y}" width="{track_w}" height="{bar_h}" rx="6" fill="{PANEL}" stroke="{BORDER}"/>
  <rect x="{bar_x}" y="{y}" width="{w}" height="{bar_h}" rx="6" fill="{c}" opacity=".2"/>
  <rect x="{bar_x}" y="{y}" width="{w}" height="{bar_h}" rx="6" fill="none" stroke="{c}" stroke-width="1.4"/>
  <text x="{bar_x+10}" y="{y+22}" fill="{cl}" font-size="13" font-weight="700">{v}</text>
  <text x="{note_x}" y="{y+21}" fill="{MUTED}" font-size="9.5">{note}</text>
'''
    s += f'''  <text x="{bar_x}" y="320" fill="{SUB}" font-size="10.5">{T["total"]}</text>
  <rect x="{bar_x}" y="334" width="460" height="58" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
  <text x="{bar_x+16}" y="360" fill="{GREEN_LIGHT}" font-size="12" font-weight="600">{T["concl"]}</text>
  <text x="{bar_x+16}" y="381" fill="{MUTED}" font-size="9.5">{T["guard"]}</text>
'''
    save("october-new-tests.svg", s + FOOTER, lang)


# ─────────────────────────────────────────────────────────
# 4. Admin 模块后移流程图
# ─────────────────────────────────────────────────────────
def chart_admin_flow(lang="zh"):
    T = {
        "zh": dict(
            title="Admin 模块后移：公开前端 → 后端独立托管",
            old=("❌ 旧：公开前端", "主站 SPA 内置 /admin 路由", "Admin 代码随 gh-pages 公开下载"),
            new=("✅ 新：后端独立托管", "FastAPI StaticFiles /admin", "公开站零 Admin 代码"),
            steps=[("主站移除", "/admin 路由\n+ 侧栏管理分组\n+ Admin chunk"),
                   ("独立构建", "admin.html\nadmin_main.js\nAdminGate 登录门"),
                   ("后端托管", "vite.admin.config.js\n→ static/admin\nFastAPI mount /admin"),
                   ("CSP 作用域", "/admin 文档专用\nunsafe-eval 放行\n公开站保持严格")],
            gate="登录门语义",
            bullets=["游客模式：自动进入（guest/superadmin）",
                     "生产环境：管理员邮箱口令登录，非管理员显示无权限",
                     "5 标签完整保留：登录记录 / 用户管理 / 后端错误 / 审计日志 / 影响证据"],
        ),
        "en": dict(
            title="Admin relocation: public frontend → backend hosting",
            old=("❌ Old: public frontend", "Main SPA bundled /admin routes", "Admin code served via gh-pages"),
            new=("✅ New: backend-hosted", "FastAPI StaticFiles /admin", "Zero admin code on public site"),
            steps=[("Site removal", "/admin routes\n+ sidebar admin group\n+ Admin chunk"),
                   ("Standalone build", "admin.html\nadmin_main.js\nAdminGate login gate"),
                   ("Backend hosting", "vite.admin.config.js\n→ static/admin\nFastAPI mount /admin"),
                   ("CSP scoping", "/admin docs only\nunsafe-eval allowed\npublic site stays strict")],
            gate="Login gate semantics",
            bullets=["Guest mode: auto-enter (guest/superadmin)",
                     "Production: admin email+password login; non-admins see no permission",
                     "All 5 tabs kept: login records / users / backend errors / audit logs / impact evidence"],
        ),
    }[lang]
    s = header(T["title"], "Admin Relocation Flow", RED)
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
  <text x="140" y="112" fill="{RED}" font-size="13" font-weight="700" text-anchor="middle">{T["old"][0]}</text>
  <text x="140" y="134" fill="{SUB}" font-size="10.5" text-anchor="middle">{T["old"][1]}</text>
  <text x="140" y="152" fill="{MUTED}" font-size="9.5" text-anchor="middle">{T["old"][2]}</text>
'''
    # 右：新状态
    s += f'''  <rect x="40" y="250" width="200" height="90" rx="10" fill="#0F241C" stroke="{GREEN}"/>
  <text x="140" y="282" fill="{GREEN_LIGHT}" font-size="13" font-weight="700" text-anchor="middle">{T["new"][0]}</text>
  <text x="140" y="304" fill="{SUB}" font-size="10.5" text-anchor="middle">{T["new"][1]}</text>
  <text x="140" y="322" fill="{MUTED}" font-size="10" text-anchor="middle">{T["new"][2]}</text>
'''
    s += arrow(140, 170, 140, 250)
    # 中间步骤
    step_colors = [(BLUE, BLUE_LIGHT), (PURPLE, PURPLE_LIGHT), (GREEN, GREEN_LIGHT), (YELLOW, YELLOW_LIGHT)]
    for i, ((t, body), (c, cl)) in enumerate(zip(T["steps"], step_colors)):
        x = 300 + i * 155
        s += f'''  <rect x="{x}" y="120" width="140" height="110" rx="10" fill="{PANEL}" stroke="{c}"/>
  <circle cx="{x+70}" cy="110" r="11" fill="{c}"/>
  <text x="{x+70}" y="114" fill="{BG}" font-size="11" font-weight="700" text-anchor="middle">{i+1}</text>
  <text x="{x+70}" y="148" fill="{cl}" font-size="11.5" font-weight="700" text-anchor="middle">{t}</text>
'''
        for j, line in enumerate(body.split("\n")):
            s += f'  <text x="{x+70}" y="{172+j*16}" fill="{SUB}" font-size="9" text-anchor="middle">{line}</text>\n'
        if i < 3:
            s += arrow(x + 140, 175, x + 155, 175)
    # 登录门语义（三点单列排布，避免长文本右溢出 viewBox）
    s += f'''  <rect x="320" y="268" width="580" height="102" rx="10" fill="{PANEL}" stroke="{PURPLE}"/>
  <text x="340" y="294" fill="{PURPLE_LIGHT}" font-size="12.5" font-weight="700">{T["gate"]}</text>
  <g font-size="10.5" fill="{SUB}">
    <circle cx="340" cy="316" r="2.5" fill="{GREEN}"/><text x="350" y="320">{T["bullets"][0]}</text>
    <circle cx="340" cy="338" r="2.5" fill="{BLUE}"/><text x="350" y="342">{T["bullets"][1]}</text>
    <circle cx="340" cy="360" r="2.5" fill="{YELLOW}"/><text x="350" y="364">{T["bullets"][2]}</text>
  </g>
'''
    save("october-admin-flow.svg", s + FOOTER, lang)


# ─────────────────────────────────────────────────────────
# 5. 游客模式架构图
# ─────────────────────────────────────────────────────────
def chart_guest_arch(lang="zh"):
    T = {
        "zh": dict(
            title="游客模式架构：全功能开放 + 生产防护",
            anon=("匿名访客", "无令牌访问"),
            switch=("GUEST_MODE 开关", "get_current_user 旁路", "security.py"),
            guest=("内置 guest 账户", "guest@evolution-ai.design", "role=superadmin · 惰性幂等创建"),
            full="全功能可达",
            feats=["• Designer / Projects / Quality", "• Deliver / DEMO / Community",
                   "• /admin 后台（游客为 superadmin）"],
            guard="生产环境防护（fail-fast）",
            bullets=["ENVIRONMENT=production 且 GUEST_MODE=true → 启动直接拒绝（与弱 SECRET_KEY 同级校验）",
                     "测试套件强制 GUEST_MODE=false（conftest），防止 401/403 语义用例被游客旁路击穿"],
        ),
        "en": dict(
            title="Guest mode: full access + production guard",
            anon=("Anonymous", "no token access"),
            switch=("GUEST_MODE switch", "get_current_user bypass", "security.py"),
            guest=("Built-in guest account", "guest@evolution-ai.design", "role=superadmin · lazily created"),
            full="Full feature access",
            feats=["• Designer / Projects / Quality", "• Deliver / DEMO / Community",
                   "• /admin console (guest = superadmin)"],
            guard="Production guard (fail-fast)",
            bullets=["ENVIRONMENT=production with GUEST_MODE=true → startup refused (same-level check as weak SECRET_KEY)",
                     "Test suite forces GUEST_MODE=false (conftest) so 401/403 semantic cases cannot be guest-bypassed"],
        ),
    }[lang]
    s = header(T["title"], "Guest Mode Architecture", YELLOW)
    # 访客（节点链整体上移至垂直居中，消除顶部大面积留白）
    s += f'''  <rect x="40" y="150" width="120" height="70" rx="10" fill="{PANEL}" stroke="{MUTED}"/>
  <text x="100" y="182" fill="{TEXT}" font-size="13" font-weight="700" text-anchor="middle">{T["anon"][0]}</text>
  <text x="100" y="202" fill="{SUB}" font-size="9.5" text-anchor="middle">{T["anon"][1]}</text>
'''
    # 旁路判定
    s += f'''  <rect x="220" y="140" width="160" height="90" rx="10" fill="#1A1230" stroke="{PURPLE}"/>
  <text x="300" y="170" fill="{PURPLE_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">{T["switch"][0]}</text>
  <text x="300" y="192" fill="{SUB}" font-size="9.5" text-anchor="middle">{T["switch"][1]}</text>
  <text x="300" y="210" fill="{MUTED}" font-size="9.5" text-anchor="middle">{T["switch"][2]}</text>
'''
    # 内置 guest
    s += f'''  <rect x="440" y="140" width="180" height="90" rx="10" fill="#0F241C" stroke="{GREEN}"/>
  <text x="530" y="170" fill="{GREEN_LIGHT}" font-size="11.5" font-weight="700" text-anchor="middle">{T["guest"][0]}</text>
  <text x="530" y="192" fill="{SUB}" font-size="10" text-anchor="middle">{T["guest"][1]}</text>
  <text x="530" y="210" fill="{MUTED}" font-size="9.5" text-anchor="middle">{T["guest"][2]}</text>
'''
    # 全功能
    s += f'''  <rect x="680" y="130" width="240" height="110" rx="10" fill="{PANEL}" stroke="{BLUE}"/>
  <text x="800" y="160" fill="{BLUE_LIGHT}" font-size="12.5" font-weight="700" text-anchor="middle">{T["full"]}</text>
  <g font-size="10" fill="{SUB}">
    <text x="700" y="184">{T["feats"][0]}</text>
    <text x="700" y="202">{T["feats"][1]}</text>
    <text x="700" y="220">{T["feats"][2]}</text>
  </g>
'''
    def arrow(x1, y1, x2, y2, c=BLUE):
        return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="1.6" marker-end="url(#g)"/>\n'
    s += '''  <defs><marker id="g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#38BDF8"/></marker></defs>
'''
    s += arrow(160, 185, 220, 185) + arrow(380, 185, 440, 185) + arrow(620, 185, 680, 185)

    # 生产防护
    s += f'''  <rect x="40" y="272" width="880" height="84" rx="10" fill="#2A1212" stroke="{RED}"/>
  <text x="60" y="300" fill="{RED}" font-size="12.5" font-weight="700">{T["guard"]}</text>
  <g font-size="10" fill="{SUB}">
    <circle cx="60" cy="322" r="2.5" fill="{RED}"/><text x="72" y="326">{T["bullets"][0]}</text>
    <circle cx="60" cy="344" r="2.5" fill="{YELLOW}"/><text x="72" y="348">{T["bullets"][1]}</text>
  </g>
'''
    save("october-guest-arch.svg", s + FOOTER, lang)


# ─────────────────────────────────────────────────────────
# 6. 8 提交时间线
# ─────────────────────────────────────────────────────────
def chart_timeline(lang="zh"):
    T = {
        "zh": dict(
            title="10 月迭代时间线（合入 main 的 8 个提交）",
            commits=[("ea41ce3b", "10-10", "NURBS 连续车身几何重构", "第二阶段 + 渲染修复", GREEN),
                     ("6df66e06", "10-10", "车漆反光调优", "轮眉渐隐消除台阶", GREEN),
                     ("4ab70371", "10-10", "整车封闭化", "7 类开口全部封闭", GREEN),
                     ("7c128f4c", "10-10", "流线型造型", "俯视收窄+斜背圆角", GREEN),
                     ("6040bac4", "10-11", "账号体系封存", "全功能游客模式+Contact", YELLOW),
                     ("a40226e6", "10-11", "京东云部署清单", "2C4G 一键部署+初始化", BLUE),
                     ("c45d9ccc", "10-11", "Admin 模块后移", "/admin 独立托管+登录门", RED),
                     ("864421d5", "10-11", "CSP 作用域修复", "unsafe-eval 仅 /admin 放行", RED)],
            head="主线 HEAD: 864421d5 （feature 分支快进合入 main）",
            groups="前 4 提交=NURBS 封闭化·造型 · 中间 2 提交=账号封存·部署 · 后 2 提交=Admin 后移·CSP 修复",
        ),
        "en": dict(
            title="October iteration timeline (8 commits merged to main)",
            commits=[("ea41ce3b", "10-10", "NURBS body rebuild", "Stage 2 + render fixes", GREEN),
                     ("6df66e06", "10-10", "Paint gloss tuning", "Fender-lip fade fixed", GREEN),
                     ("4ab70371", "10-10", "Body fully sealed", "7 openings closed", GREEN),
                     ("7c128f4c", "10-10", "Streamlined styling", "Plan taper + fastback", GREEN),
                     ("6040bac4", "10-11", "Accounts archived", "Full guest mode+Contact", YELLOW),
                     ("a40226e6", "10-11", "JD Cloud deploy kit", "2C4G one-click setup", BLUE),
                     ("c45d9ccc", "10-11", "Admin relocation", "/admin hosting + gate", RED),
                     ("864421d5", "10-11", "CSP scope fix", "unsafe-eval /admin only", RED)],
            head="Mainline HEAD: 864421d5 (feature branch fast-forwarded into main)",
            groups="First 4 = NURBS closure & styling · middle 2 = accounts & deploy · last 2 = Admin relocation & CSP fix",
        ),
    }[lang]
    s = header(T["title"], "Iteration Timeline", BLUE)
    commits = T["commits"]
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
            s += f'  <text x="{x}" y="{by+20}" fill="{TEXT}" font-size="10.5" font-weight="700" text-anchor="middle">{title}</text>\n'
            s += f'  <text x="{x}" y="{by+40}" fill="{SUB}" font-size="9" text-anchor="middle">{sub}</text>\n'
            s += f'  <text x="{x}" y="{by+55}" fill="{MUTED}" font-size="8.5" text-anchor="middle" font-family="Consolas,monospace">{h}</text>\n'
        else:
            by = y_line - 96
            s += f'  <rect x="{x-72}" y="{by}" width="144" height="62" rx="8" fill="{PANEL}" stroke="{c}"/>\n'
            s += f'  <text x="{x}" y="{by+20}" fill="{TEXT}" font-size="10.5" font-weight="700" text-anchor="middle">{title}</text>\n'
            s += f'  <text x="{x}" y="{by+40}" fill="{SUB}" font-size="9" text-anchor="middle">{sub}</text>\n'
            s += f'  <text x="{x}" y="{by+55}" fill="{MUTED}" font-size="8.5" text-anchor="middle" font-family="Consolas,monospace">{h}</text>\n'
    s += f'''  <rect x="80" y="350" width="800" height="50" rx="10" fill="{PANEL}" stroke="{BORDER}"/>
  <text x="100" y="374" fill="{GREEN_LIGHT}" font-size="11.5" font-weight="600">{T["head"]}</text>
  <text x="100" y="392" fill="{MUTED}" font-size="9.5">{T["groups"]}</text>
'''
    save("october-timeline.svg", s + FOOTER, lang)


# ─────────────────────────────────────────────────────────
# 7. 7 类开口封闭分类
# ─────────────────────────────────────────────────────────
def chart_closure(lang="zh"):
    T = {
        "zh": dict(
            title="整车 7 类开口封闭（拓扑对齐规范）",
            cats=[("前脸中央封板", "前保与机舱之间", GREEN),
                  ("尾门封板", "尾门开口封闭", GREEN),
                  ("A/C 柱三角楔", "柱与玻璃共边", PURPLE),
                  ("cowl 封条", "机盖→风挡过渡", BLUE),
                  ("底盘托盘", "底部全封闭", BLUE),
                  ("轮拱内衬", "轮拱开口内衬", YELLOW),
                  ("内饰搁板", "防透视封堵", RED)],
            spec="尺寸·装配·拓扑对齐规范",
            verify="验证：test_car_topology_closure.py · 12/12 全通过",
            covers="覆盖横链边重合、cowl 封条、柱楔共边、底盘封闭、前后封板、俯视收窄、门框压条、轮拱内衬、防透视搁板、零件普查",
            covers_size="10.5",
        ),
        "en": dict(
            title="7 body opening categories sealed (topology alignment spec)",
            cats=[("Front center panel", "Between bumper & bay", GREEN),
                  ("Tailgate panel", "Tailgate opening sealed", GREEN),
                  ("A/C-pillar wedge", "Pillar-glass shared edge", PURPLE),
                  ("Cowl seal", "Hood→windshield transition", BLUE),
                  ("Underbody tray", "Fully sealed underbody", BLUE),
                  ("Arch liners", "Wheel-arch opening liners", YELLOW),
                  ("Interior shelf", "Blocks see-through view", RED)],
            spec="Dim · fit · topology aligned",
            verify="Verified: test_car_topology_closure.py · 12/12 all pass",
            covers="Covers edge coincidence, cowl seal, pillar wedge, underbody closure, front/rear panels, plan taper, door-sill overlap, arch liners, see-through shelf, part census",
            covers_size="9.5",
        ),
    }[lang]
    s = header(T["title"], "Body Opening Closure", GREEN)
    cats = T["cats"]
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
  <text x="{x+44}" y="{y+35}" fill="{TEXT}" font-size="12" font-weight="700">{name}</text>
  <text x="{x+20}" y="{y+66}" fill="{SUB}" font-size="10">{desc}</text>
  <text x="{x+20}" y="{y+88}" fill="{MUTED}" font-size="9">{T["spec"]}</text>
'''
    s += f'''  <rect x="70" y="330" width="820" height="70" rx="10" fill="#0F241C" stroke="{GREEN}"/>
  <text x="90" y="358" fill="{GREEN_LIGHT}" font-size="12.5" font-weight="700">{T["verify"]}</text>
  <text x="90" y="380" fill="{SUB}" font-size="{T["covers_size"]}">{T["covers"]}</text>
'''
    save("october-closure.svg", s + FOOTER, lang)


# ─────────────────────────────────────────────────────────
# 8. 部署拓扑图
# ─────────────────────────────────────────────────────────
def chart_deployment(lang="zh"):
    T = {
        "zh": dict(
            title="生产部署拓扑（内地合规 + 同域反代）",
            browser=("浏览器", "用户端"),
            nginx=("Nginx (TLS)", "同域反代", "/ → dist 静态", "/api & /admin → 后端"),
            pages=("GitHub Pages / dist", "公开静态站（零 Admin 代码）"),
            backend=("FastAPI 后端", "/api/v1/* 业务接口", "/admin 独立后台", "GUEST_MODE（封存期）"),
            db=("PostgreSQL + Redis", "数据 + 会话/限流"),
            cloud=("京东云 2C4G（内地合规）", "2G swap · Docker 四服务栈", "域名转入境内 + ICP 备案",
                   "含微信扫码须内地服务器", "PIPL 数据不出境"),
            host="部署承载",
        ),
        "en": dict(
            title="Production topology (mainland compliance + same-origin proxy)",
            browser=("Browser", "User side"),
            nginx=("Nginx (TLS)", "Same-origin proxy", "/ → dist static", "/api & /admin → backend"),
            pages=("GitHub Pages / dist", "Public site (zero admin code)"),
            backend=("FastAPI backend", "/api/v1/* business APIs", "/admin standalone console", "GUEST_MODE (mothballed)"),
            db=("PostgreSQL + Redis", "Data + sessions/rate-limit"),
            cloud=("JD Cloud 2C4G (CN compliant)", "2G swap · 4-service Docker stack", "Domain onshore + ICP filing",
                   "WeChat QR needs mainland server", "PIPL: data stays onshore"),
            host="Hosts",
        ),
    }[lang]
    s = header(T["title"], "Deployment Topology", BLUE)
    # 浏览器
    s += f'''  <rect x="40" y="190" width="110" height="60" rx="10" fill="{PANEL}" stroke="{MUTED}"/>
  <text x="95" y="218" fill="{TEXT}" font-size="12" font-weight="700" text-anchor="middle">{T["browser"][0]}</text>
  <text x="95" y="236" fill="{SUB}" font-size="10" text-anchor="middle">{T["browser"][1]}</text>
'''
    # Nginx
    s += f'''  <rect x="210" y="170" width="150" height="100" rx="10" fill="#0B1A2E" stroke="{BLUE}"/>
  <text x="285" y="200" fill="{BLUE_LIGHT}" font-size="12.5" font-weight="700" text-anchor="middle">{T["nginx"][0]}</text>
  <text x="285" y="222" fill="{SUB}" font-size="10" text-anchor="middle">{T["nginx"][1]}</text>
  <text x="285" y="240" fill="{MUTED}" font-size="9.5" text-anchor="middle">{T["nginx"][2]}</text>
  <text x="285" y="256" fill="{MUTED}" font-size="9" text-anchor="middle">{T["nginx"][3]}</text>
'''
    # 静态站
    s += f'''  <rect x="420" y="70" width="180" height="70" rx="10" fill="{PANEL}" stroke="{GREEN}"/>
  <text x="510" y="100" fill="{GREEN_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">{T["pages"][0]}</text>
  <text x="510" y="120" fill="{SUB}" font-size="9.5" text-anchor="middle">{T["pages"][1]}</text>
'''
    # 后端
    s += f'''  <rect x="420" y="170" width="180" height="100" rx="10" fill="#0F241C" stroke="{PURPLE}"/>
  <text x="510" y="200" fill="{PURPLE_LIGHT}" font-size="12.5" font-weight="700" text-anchor="middle">{T["backend"][0]}</text>
  <text x="510" y="220" fill="{SUB}" font-size="10" text-anchor="middle">{T["backend"][1]}</text>
  <text x="510" y="238" fill="{SUB}" font-size="10" text-anchor="middle">{T["backend"][2]}</text>
  <text x="510" y="256" fill="{MUTED}" font-size="9.5" text-anchor="middle">{T["backend"][3]}</text>
'''
    # 数据层
    s += f'''  <rect x="420" y="290" width="180" height="70" rx="10" fill="{PANEL}" stroke="{YELLOW}"/>
  <text x="510" y="320" fill="{YELLOW_LIGHT}" font-size="12" font-weight="700" text-anchor="middle">{T["db"][0]}</text>
  <text x="510" y="340" fill="{SUB}" font-size="10" text-anchor="middle">{T["db"][1]}</text>
'''
    # 京东云
    s += f'''  <rect x="680" y="150" width="220" height="130" rx="10" fill="#1A1230" stroke="{PURPLE}" stroke-dasharray="4 3"/>
  <text x="790" y="178" fill="{PURPLE_LIGHT}" font-size="11.5" font-weight="700" text-anchor="middle">{T["cloud"][0]}</text>
  <text x="790" y="198" fill="{SUB}" font-size="10" text-anchor="middle">{T["cloud"][1]}</text>
  <text x="790" y="216" fill="{SUB}" font-size="10" text-anchor="middle">{T["cloud"][2]}</text>
  <text x="790" y="234" fill="{MUTED}" font-size="9.5" text-anchor="middle">{T["cloud"][3]}</text>
  <text x="790" y="256" fill="{YELLOW_LIGHT}" font-size="9.5" text-anchor="middle">{T["cloud"][4]}</text>
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
    s += f'  <text x="640" y="212" fill="{MUTED}" font-size="9" text-anchor="middle">{T["host"]}</text>'
    save("october-deployment.svg", s + FOOTER, lang)


# ─────────────────────────────────────────────────────────
# 9. CSP 作用域关系图
# ─────────────────────────────────────────────────────────
def chart_csp_scope(lang="zh"):
    T = {
        "zh": dict(
            title="CSP 作用域：/admin 放行 unsafe-eval · 其余严格",
            pub=("公开 API + 主站（默认严格）", "script-src 'self'", "无 unsafe-eval · 拦截 vue-i18n Function 构造器",
                 "/api/v1/* · evolution-ai.design 首页"),
            adm=("/admin 文档（专用放宽）", "script-src 'self' 'unsafe-eval'", "仅允许 Function 构造器供 vue-i18n 编译",
                 "/admin/ · /admin/assets/*"),
            mw="按请求路径选择 CSP 策略",
            defect="缺陷与修复",
            d1="首测后台白屏：EvalError - 'unsafe-eval' is not an allowed source of script",
            d2="修复：/admin 文档作用域单独放行 unsafe-eval；回归测试锁定边界（test_admin_console.py）",
        ),
        "en": dict(
            title="CSP scope: unsafe-eval for /admin only, strict elsewhere",
            pub=("Public API + main site (strict default)", "script-src 'self'", "No unsafe-eval · blocks vue-i18n Function constructor",
                 "/api/v1/* · evolution-ai.design home"),
            adm=("/admin docs (scoped relaxation)", "script-src 'self' 'unsafe-eval'", "Allows Function constructor only for vue-i18n compilation",
                 "/admin/ · /admin/assets/*"),
            mw="Selects CSP policy per request path",
            defect="Defect & fix",
            d1="First-run white screen: EvalError - 'unsafe-eval' is not an allowed source of script",
            d2="Fix: /admin-scope unsafe-eval only; boundary locked by test_admin_console.py",
        ),
    }[lang]
    s = header(T["title"], "CSP Scoping", YELLOW)
    # 全局严格
    s += f'''  <rect x="60" y="80" width="380" height="130" rx="12" fill="{PANEL}" stroke="{GREEN}"/>
  <text x="250" y="110" fill="{GREEN_LIGHT}" font-size="13" font-weight="700" text-anchor="middle">{T["pub"][0]}</text>
  <text x="250" y="134" fill="{LABEL}" font-size="11" text-anchor="middle" font-family="Consolas,monospace">{T["pub"][1]}</text>
  <text x="250" y="154" fill="{MUTED}" font-size="9.5" text-anchor="middle">{T["pub"][2]}</text>
  <text x="250" y="176" fill="{SUB}" font-size="10.5" text-anchor="middle">{T["pub"][3]}</text>
'''
    # /admin 作用域
    s += f'''  <rect x="520" y="80" width="380" height="130" rx="12" fill="#1A1230" stroke="{PURPLE}"/>
  <text x="710" y="110" fill="{PURPLE_LIGHT}" font-size="13" font-weight="700" text-anchor="middle">{T["adm"][0]}</text>
  <text x="710" y="134" fill="{LABEL}" font-size="11" text-anchor="middle" font-family="Consolas,monospace">{T["adm"][1]}</text>
  <text x="710" y="154" fill="{MUTED}" font-size="9.5" text-anchor="middle">{T["adm"][2]}</text>
  <text x="710" y="176" fill="{SUB}" font-size="10.5" text-anchor="middle">{T["adm"][3]}</text>
'''
    # 中间判定
    s += f'''  <rect x="380" y="240" width="200" height="70" rx="10" fill="#0B101A" stroke="{BLUE}"/>
  <text x="480" y="268" fill="{BLUE_LIGHT}" font-size="11.5" font-weight="700" text-anchor="middle">SecurityHeadersMiddleware</text>
  <text x="480" y="288" fill="{SUB}" font-size="9.5" text-anchor="middle">{T["mw"]}</text>
'''
    s += '''  <defs><marker id="c" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#38BDF8"/></marker></defs>
'''
    s += f'  <line x1="250" y1="210" x2="420" y2="240" stroke="{GREEN}" stroke-width="1.6" marker-end="url(#c)"/>\n'
    s += f'  <line x1="710" y1="210" x2="540" y2="240" stroke="{PURPLE}" stroke-width="1.6" marker-end="url(#c)"/>\n'
    # 缺陷→修复
    s += f'''  <rect x="60" y="330" width="840" height="70" rx="10" fill="#2A1212" stroke="{RED}"/>
  <text x="80" y="356" fill="{RED}" font-size="11.5" font-weight="700">{T["defect"]}</text>
  <g font-size="9.5" fill="{SUB}">
    <circle cx="80" cy="378" r="2.5" fill="{RED}"/><text x="92" y="382">{T["d1"]}</text>
    <circle cx="500" cy="378" r="2.5" fill="{GREEN}"/><text x="512" y="382">{T["d2"]}</text>
  </g>
'''
    save("october-csp-scope.svg", s + FOOTER, lang)


if __name__ == "__main__":
    for lang in ("zh", "en"):
        chart_test_results(lang)
        chart_regression_donut(lang)
        chart_new_tests(lang)
        chart_admin_flow(lang)
        chart_guest_arch(lang)
        chart_timeline(lang)
        chart_closure(lang)
        chart_deployment(lang)
        chart_csp_scope(lang)
    print("done")
