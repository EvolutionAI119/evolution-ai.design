#!/usr/bin/env python3
"""
EVOLUTION AI 文档-源码一致性一键核对脚本（Python 标准库，无需安装依赖）。

检查内容：
1. 事实提取：HTTP 端点数 / ORM 表数 / 前端页面数 / CarParams 字段数 / 贝叶斯空间维数
2. 链接校验：README.md、docs/*.md、algorithm_model/README.md 中的相对链接
3. 导航完整性：docs 下每个 .md 都应出现在 README.md 链接目标中

退出码：存在死链时为 1，其余情况为 0。
file:/// 本机链接不作为失败，但会单独列出（可移植性问题，建议改为相对路径）。
"""
import os
import re
import sys


def root_dir() -> str:
    # check_consistency.py -> scripts -> doc-code-audit -> skills -> .trae -> root
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))))))


# ---------------------------------------------------------------
# 1. 事实提取
# ---------------------------------------------------------------

def fact_endpoints(root: str) -> dict:
    routes_dir = os.path.join(root, "backend", "app", "routes")
    per_module = {}
    module_total = 0
    method_re = re.compile(r"(get|post|put|delete|patch)\(")
    for name in sorted(os.listdir(routes_dir)):
        if not name.endswith(".py"):
            continue
        text = open(os.path.join(routes_dir, name), encoding="utf-8").read()
        router_names = re.findall(r"^(\w+)\s*=\s*APIRouter\(", text, re.M)
        n = 0
        for rn in router_names:
            n += len(re.findall(r"@" + rn + r"\.(?:get|post|put|delete|patch)\(",
                                text))
        if n:
            per_module[name] = n
            module_total += n
    main_text = open(os.path.join(root, "backend", "app", "main.py"),
                     encoding="utf-8").read()
    system_endpoints = len(re.findall(
        r"@app\.(?:get|post|put|delete|patch)\(", main_text))
    return {
        "per_module": per_module,
        "module_total": module_total,
        "system_endpoints": system_endpoints,
        "grand_total": module_total + system_endpoints,
    }


def fact_orm_tables(root: str) -> int:
    text = open(os.path.join(root, "backend", "app", "database.py"),
                encoding="utf-8").read()
    return len(re.findall(r"__tablename__", text))


def fact_frontend_pages(root: str) -> int:
    text = open(os.path.join(root, "src", "router.js"), encoding="utf-8").read()
    # 路由记录同一行同时含 path 与 name；守卫的对象 return 只含其一，借此排除
    return len(re.findall(r"^[^\n]*path:[^\n]*name:", text, re.M))


def fact_carparams_fields(root: str) -> int:
    text = open(os.path.join(root, "algorithm_model", "car_modeling",
                             "car_params.py"), encoding="utf-8").read()
    return len(re.findall(r"^    [A-Za-z_]\w*:\s", text, re.M))


def fact_bayes_space_dim(root: str) -> int:
    text = open(os.path.join(root, "backend", "app", "bayes_optimizer.py"),
                encoding="utf-8").read()
    # 注意类型标注 List[...] 的括号在 '= [' 之前
    m = re.search(r"DEFAULT_SPACE[^=]*=\s*\[(.*?)\n\]", text, re.S)
    return len(re.findall(r'"name"', m.group(1) if m else ""))


# ---------------------------------------------------------------
# 2. 链接校验 + 3. 导航完整性
# ---------------------------------------------------------------

def markdown_files(root: str):
    files = ["README.md", os.path.join("algorithm_model", "README.md")]
    docs = os.path.join(root, "docs")
    for name in sorted(os.listdir(docs)):
        if name.endswith(".md"):
            files.append(os.path.join("docs", name))
    return files


def check_links(root: str):
    link_re = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    broken, file_urls = [], []
    for rel in markdown_files(root):
        path = os.path.join(root, rel)
        base = os.path.dirname(path)
        for _label, target in link_re.findall(
                open(path, encoding="utf-8").read()):
            if re.match(r"https?://", target) or target.startswith(
                    ("#", "mailto:")):
                continue
            if target.startswith("file:///"):
                file_urls.append((rel, target))
                continue
            t = target.split("#", 1)[0]
            if t and not os.path.exists(os.path.normpath(os.path.join(base, t))):
                broken.append((rel, target))
    return broken, file_urls


def check_readme_nav(root: str):
    readme = open(os.path.join(root, "README.md"), encoding="utf-8").read()
    targets = set(re.findall(r"\[[^\]]*\]\(([^)]+)\)", readme))
    missing = []
    for name in sorted(os.listdir(os.path.join(root, "docs"))):
        if name.endswith(".md") and not any(
                t.endswith(name) for t in targets):
            missing.append(name)
    return missing


# ---------------------------------------------------------------
# main
# ---------------------------------------------------------------

def main() -> int:
    root = root_dir()
    print("=" * 66)
    print("EVOLUTION AI 文档-源码一致性核对")
    print("=" * 66)

    ep = fact_endpoints(root)
    print("\n[1] 事实基线（来自源码）")
    print(f"  HTTP 端点总数      : {ep['grand_total']} "
          f"(路由模块 {ep['module_total']} + 系统端点 {ep['system_endpoints']})")
    for name, n in ep["per_module"].items():
        print(f"      {n:3d}  {name}")
    print(f"  ORM 表数           : {fact_orm_tables(root)}")
    print(f"  前端页面数         : {fact_frontend_pages(root)}")
    print(f"  CarParams 字段数   : {fact_carparams_fields(root)}")
    print(f"  贝叶斯空间维数     : {fact_bayes_space_dim(root)}")

    broken, file_urls = check_links(root)
    print("\n[2] Markdown 相对链接校验")
    if broken:
        for rel, target in broken:
            print(f"  BROKEN  {rel}  ->  {target}")
    else:
        print("  死链：0")
    if file_urls:
        print("  file:/// 本机链接（建议改为仓库相对路径）：")
        for rel, target in file_urls:
            print(f"  FILEURL {rel}  ->  {target}")

    missing_nav = check_readme_nav(root)
    print("\n[3] README 文档导航完整性")
    if missing_nav:
        for name in missing_nav:
            print(f"  MISSING-IN-NAV  docs/{name}")
    else:
        print("  docs 下所有 .md 均已在 README 导航中")

    print("\n" + "=" * 66)
    if broken:
        print(f"结果：失败（{len(broken)} 个死链）")
        return 1
    print("结果：通过（无死链；请人工比对 [1] 事实与文档陈述）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
