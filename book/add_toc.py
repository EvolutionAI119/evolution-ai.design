# 为《AI 原生软件开发方法论》PDF 添加目录页与页码
# 流程：1) 逐页提取文本定位各章起始页  2) 生成目录页（含点线引导与页码）
#       3) 每页页脚盖章页码  4) 目录插入封面之后，章页码加上目录偏移
import io, sys, re
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

pdfmetrics.registerFont(TTFont('CJK', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('CJK-Bold', 'C:/Windows/Fonts/msyhbd.ttc', subfontIndex=0))

CHAPTERS_ZH = [
    ('00-framework-map', '框架地图'),
    ('01-ai-native-software', '第 1 章 · AI 原生软件的定义与边界'),
    ('02-complex-giant-systems', '第 2 章 · 开放的复杂巨系统'),
    ('03-metasynthesis', '第 3 章 · 从定性到定量：综合集成方法'),
    ('04-five-layer-architecture', '第 4 章 · 五层架构与薄壳编排'),
    ('05-dual-geometry-core', '第 5 章 · 一个向量，四种表达'),
    ('06-contract-first-interfaces', '第 6 章 · 契约优先的接口设计'),
    ('07-unified-workbench-frontend', '第 7 章 · 统一工作台：12 个页面的信息架构'),
    ('08-bayesian-optimization', '第 8 章 · 代理模型与贝叶斯优化'),
    ('09-dl-llm-fusion', '第 9 章 · 深度学习与 LLM 融合层'),
    ('10-semantic-interfaces', '第 10 章 · 语义接口：从纹理到品牌 DNA'),
    ('11-testing-pyramid', '第 11 章 · 测试金字塔与 1000+ 例基线'),
    ('12-observability-audit', '第 12 章 · 可观测性与全链路审计'),
    ('13-security-guardrails', '第 13 章 · 安全围栏与游客模式'),
    ('14-build-deploy-release', '第 14 章 · 构建、部署与发布'),
    ('15-general-design-department', '第 15 章 · 总体设计部：人机结合的研讨厅'),
    ('16-knowledge-document-system', '第 16 章 · 文档即产品：知识底座与一致性审计'),
    ('17-team-roles-rhythm', '第 17 章 · AI 原生团队的角色与节奏'),
    ('18-fast-slow-variables', '第 18 章 · 快变量与序参量：深度演化七项纲领'),
    ('appendix-a-glossary', '附录 A · 术语表'),
    ('appendix-b-checklists', '附录 B · 检查清单'),
    ('appendix-c-baseline-facts', '附录 C · 本平台事实基线'),
    ('appendix-d-references', '附录 D · 参考文献'),
]
CHAPTERS_EN = [
    ('00-framework-map', 'Framework Map'),
    ('01-ai-native-software', 'Ch.1 · Defining AI-Native Software'),
    ('02-complex-giant-systems', 'Ch.2 · Open Complex Giant Systems'),
    ('03-metasynthesis', 'Ch.3 · Qualitative-to-Quantitative Metasynthesis'),
    ('04-five-layer-architecture', 'Ch.4 · Five-Layer Architecture & Thin Orchestration'),
    ('05-dual-geometry-core', 'Ch.5 · One Vector, Four Expressions'),
    ('06-contract-first-interfaces', 'Ch.6 · Contract-First Interface Design'),
    ('07-unified-workbench-frontend', 'Ch.7 · Unified Workbench: 12 Pages'),
    ('08-bayesian-optimization', 'Ch.8 · Surrogate Models & Bayesian Optimization'),
    ('09-dl-llm-fusion', 'Ch.9 · DL & LLM Fusion Layer'),
    ('10-semantic-interfaces', 'Ch.10 · Semantic Interfaces: Texture to Brand DNA'),
    ('11-testing-pyramid', 'Ch.11 · Testing Pyramid & the 955 Baseline'),
    ('12-observability-audit', 'Ch.12 · Observability & Full-Chain Audit'),
    ('13-security-guardrails', 'Ch.13 · Security Guardrails & Guest Mode'),
    ('14-build-deploy-release', 'Ch.14 · Build, Deploy & Release'),
    ('15-general-design-department', 'Ch.15 · The General Design Department'),
    ('16-knowledge-document-system', 'Ch.16 · Docs as Product'),
    ('17-team-roles-rhythm', 'Ch.17 · Roles & Rhythm of AI-Native Teams'),
    ('18-fast-slow-variables', 'Ch.18 · Fast/Slow Variables: Seven Guidelines'),
    ('appendix-a-glossary', 'Appendix A · Glossary'),
    ('appendix-b-checklists', 'Appendix B · Checklists'),
    ('appendix-c-baseline-facts', 'Appendix C · Baseline Facts'),
    ('appendix-d-references', 'Appendix D · References'),
]

def norm(s):
    return re.sub(r'\s+', '', s)

def find_chapter_pages(reader, chapters):
    """在每一页找章节标题（H1 渲染后的纯文本），返回 {slug: 1-based 页码}"""
    page_texts = [norm(p.extract_text() or '') for p in reader.pages]
    starts, cursor = {}, 0
    for slug, title in chapters:
        # 用标题正文的 H1 文本（md 里的 # 标题），从 chapters 标题里抽关键词
        key = None
        for probe in [title]:
            pass
        # 直接用 markdown 文件首行 H1 更稳，由调用方传入
        raise RuntimeError('use md titles')
    return starts

def md_h1_titles(lang, chapters):
    out = []
    for slug, disp in chapters:
        with open(f'{lang}/{slug}.md', encoding='utf-8') as f:
            for line in f:
                if line.startswith('# '):
                    out.append((slug, disp, line[2:].strip()))
                    break
    return out

def locate(reader, entries):
    page_texts = [norm(p.extract_text() or '') for p in reader.pages]
    starts, cur = {}, 1
    for slug, disp, h1 in entries:
        k = norm(h1)
        cands = [k[:24], k[:16], k[:10]]
        # 去掉「第 N 章」「Ch.N」前缀后的核心词，作为最后兜底
        core = re.sub(r'^(第[0-9０-９]+章|Ch\.?\s*[0-9]+)', '', k)
        core = re.sub(r'^[·:.\-]+', '', core)
        if len(core) >= 6:
            cands.append(core[:14])
        hit = None
        for i in range(cur - 1, len(page_texts)):
            if any(c and c in page_texts[i] for c in cands):
                hit = i + 1
                break
        if hit:
            starts[slug] = hit
            cur = hit
        else:
            print(f'  ⚠ 未定位: {slug} ({h1[:30]})')
    return starts

def make_toc_pages(entries, starts, offset, is_zh):
    """生成目录 PDF（可能多页），返回 bytes 与页数"""
    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)
    title = '目录' if is_zh else 'Contents'
    line_h, per_page = 26, 24
    y0 = H - 120
    c.setFont('CJK-Bold', 22)
    c.drawString(72, H - 72, title)
    c.setLineWidth(2)
    c.line(72, H - 84, W - 72, H - 84)
    page_count = 1
    y = y0
    for idx, (slug, disp, h1) in enumerate(entries):
        if y < 72:
            c.showPage(); page_count += 1; y = H - 72
        page_no = starts.get(slug, 0) + offset
        c.setFont('CJK', 11.5)
        c.drawString(72, y, disp)
        tw = pdfmetrics.stringWidth(disp, 'CJK', 11.5)
        nw = pdfmetrics.stringWidth(str(page_no), 'CJK', 11.5)
        c.drawRightString(W - 72, y, str(page_no))
        # 点线引导
        c.setDash(1, 3)
        c.setLineWidth(0.5)
        c.line(72 + tw + 8, y + 3, W - 72 - nw - 8, y + 3)
        c.setDash()
        y -= line_h
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read(), page_count

def stamp_page_numbers(reader, skip_first_n, is_zh):
    """返回 {0-based 页索引: 页码覆盖层 PDF bytes}；封面(skip_first_n)不盖章"""
    overlays = {}
    total = len(reader.pages)
    for i in range(skip_first_n, total):
        buf = io.BytesIO()
        first = reader.pages[i]
        w = float(first.mediabox.width); h = float(first.mediabox.height)
        c = canvas.Canvas(buf, pagesize=(w, h))
        c.setFont('CJK', 9)
        label = f'- {i + 1} -'
        c.drawCentredString(w / 2, 24, label)
        c.save()
        buf.seek(0)
        overlays[i] = buf.read()
    return overlays

def process(src, dst, lang, chapters):
    is_zh = lang == 'zh'
    reader = PdfReader(src)
    entries = md_h1_titles(lang, chapters)
    starts = locate(reader, entries)
    print(f'  定位到 {len(starts)}/{len(entries)} 章')
    # 目录页数需要两遍：先假设 offset=2 估算页数，再用真实页数重算
    toc_bytes, toc_pages = make_toc_pages(entries, starts, 2, is_zh)
    toc_bytes, toc_pages = make_toc_pages(entries, starts, toc_pages, is_zh)
    toc_reader = PdfReader(io.BytesIO(toc_bytes))
    overlays = stamp_page_numbers(reader, 1, is_zh)  # 跳过封面
    writer = PdfWriter()
    writer.add_page(reader.pages[0])  # 封面
    for p in toc_reader.pages:
        writer.add_page(p)
    for i in range(1, len(reader.pages)):
        page = reader.pages[i]
        if i in overlays:
            ov = PdfReader(io.BytesIO(overlays[i])).pages[0]
            page.merge_page(ov)
        writer.add_page(page)
    with open(dst, 'wb') as f:
        writer.write(f)
    print(f'  ✓ {dst}  总页数={len(reader.pages) + toc_pages}（目录 {toc_pages} 页）')

process('ai-native-software-development.zh.pdf', 'AI原生软件开发方法论-中文.pdf', 'zh', CHAPTERS_ZH)
process('ai-native-software-development.en.pdf', 'AI-Native-Software-Development-EN.pdf', 'en', CHAPTERS_EN)
