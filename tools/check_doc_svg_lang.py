"""文档-图表语言一致性校验（防回归闸门）。

红线规则：
  1. docs/en/ 下的英文文档引用的 SVG 不得包含中文（CJK）文字；
     —— 英文文档应引用 docs/images/en/ 下的英文版图，或不含文字的共享图。
  2. docs/ 根下的中文文档不得引用 docs/images/en/ 下的英文版 SVG。

用法: python tools/check_doc_svg_lang.py
退出码: 0=全部通过, 1=存在违规（逐条打印）。
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = os.path.join(ROOT, "docs")
DOCS_EN = os.path.join(DOCS, "en")

CJK = re.compile(r"[一-鿿]")
# <img src="docs/images/xxx.svg"> 与 markdown ![](docs/images/xxx.svg)
IMG = re.compile(r'(?:src="|!\[[^\]]*\]\()\s*(docs/images/[^"\)\s]+\.svg)', re.I)

# 位于 docs/ 根但内容为纯英文的文档（规范豁免：统一使用英文 SVG 与英文术语）
EN_DOC_NAMES = {"EVOLUTION_AI_paper.md"}


def md_files(base):
    for dirpath, _, names in os.walk(base):
        for n in names:
            if n.lower().endswith(".md"):
                yield os.path.join(dirpath, n)


def check():
    violations = []
    # 英文文档（docs/en/ + 豁免清单内的英文论文）：引用的 SVG 不得含中文
    def check_en(md):
        with open(md, encoding="utf-8") as f:
            text = f.read()
        for ref in IMG.findall(text):
            svg_path = os.path.join(ROOT, ref.replace("/", os.sep))
            if not os.path.isfile(svg_path):
                violations.append(f"[缺失] {os.path.relpath(md, ROOT)} 引用了不存在的 {ref}")
                continue
            with open(svg_path, encoding="utf-8") as f:
                svg = f.read()
            nonlocal_checked[0] += 1
            if CJK.search(svg):
                violations.append(
                    f"[中英混排] {os.path.relpath(md, ROOT)} 引用了含中文文字的 {ref}"
                    "（应改用 docs/images/en/ 英文版）"
                )

    nonlocal_checked = [0]
    for md in md_files(DOCS_EN):
        check_en(md)
    # 中文文档：不得引用 en/ 目录的 SVG；英文论文豁免文件改按英文规则校验
    for md in md_files(DOCS):
        if os.path.dirname(md).startswith(DOCS_EN):
            continue
        if os.path.basename(md) in EN_DOC_NAMES:
            check_en(md)
            continue
        with open(md, encoding="utf-8") as f:
            text = f.read()
        for ref in IMG.findall(text):
            if ref.startswith("docs/images/en/"):
                violations.append(
                    f"[引用错位] {os.path.relpath(md, ROOT)} 是中文文档却引用英文版 {ref}"
                )
    return violations, nonlocal_checked[0]


if __name__ == "__main__":
    vs, n = check()
    if vs:
        print(f"✗ 文档-图表语言一致性校验失败（{len(vs)} 项违规，已检查 {n} 张 SVG）：")
        for v in vs:
            print("  " + v)
        sys.exit(1)
    print(f"✓ 文档-图表语言一致性校验通过（{n} 张 SVG 引用全部合规）")
    sys.exit(0)
