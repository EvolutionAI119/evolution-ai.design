#!/usr/bin/env python3
"""提交前门禁：结构事实 + 文档口径 + SISA 隔离。

用法：python scripts/pre_commit_check.py
退出码：0 通过；1 有漂移或越界。
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_facts import ROOT, collect_facts  # noqa: E402

os.chdir(ROOT)

EXPECTED_FACTS = {
    'modules': 19,
    'routes_total': 152,
    'main_direct': 2,
    'tables': 17,
    'formats': 20,
    'router_paths': 12,
    'carparams': 22,
    'bayes_space': 14,
}

CURRENT_DOCS = [
    'README.md',
    'docs/ARCHITECTURE_DESIGN.md',
    'book/README.md',
    '.trae/agents/evolution-ai-design.md',
    'docs/2D_LAYOUT_VERIFICATION.md',
]

# 只匹配“当作当前基线”的旧口径；带历史/作废/取代/快照的行自动放行。
STALE_PATTERNS = [
    (r'前端\s*416', '前端旧基线 416'),
    (r'frontend\s*416', 'frontend 旧基线 416'),
    (r'基线\s*(204|123|416)', '旧测试基线'),
    (r'\b955\b', '旧测试合计 955'),
    (r'\b153\s*个?\s*(HTTP\s*)?端点', '旧端点数 153'),
    (r'\b151\s*个?\s*端点', '旧端点数 151'),
    (r'\b118\s*端', '旧端点数 118'),
    (r'\b13\s*张表', '旧表数 13'),
    (r'710/710', '旧测试数 710'),
    (r'\b771\s*(/|项|个)', '旧前端基线 771'),
    (r'\b388\b', '旧后端基线 388'),
    (r'\b205\b', '旧算法基线 205'),
]
ALLOW_LINE = ('历史', '作废', '旧快照', '快照', '取代', '已被', '迁移', '复盘')

FORBIDDEN_MODULES = [
    'iges_nurbs', 'iges_reader', 'nurbs_curvature', 'panel_split', 'surface_grade',
    'graded_surface', 'quality_assessment', 'proximity_filter', 'dna_mapping',
    'car_concept', 'feature_plugins', 'build_pipeline', 'gh_export',
    'batch_a_surface', 'inference',
]
CODE_EXT = {'.py', '.js', '.vue', '.ts', '.json', '.yaml', '.yml', '.ps1', '.cjs', '.sh'}


def check_facts(errors):
    _, facts = collect_facts()
    for key, expected in EXPECTED_FACTS.items():
        if facts.get(key) != expected:
            errors.append(f'[facts] {key}={facts.get(key)}，期望 {expected}')
    if not errors:
        print('[facts] OK  ' + ' '.join(f'{k}={v}' for k, v in facts.items()))


def check_docs(errors):
    for rel in CURRENT_DOCS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            errors.append(f'[docs] 缺少 {rel}')
            continue
        for lineno, line in enumerate(open(path, encoding='utf-8', errors='ignore'), 1):
            if any(word in line for word in ALLOW_LINE):
                continue
            for pattern, label in STALE_PATTERNS:
                if re.search(pattern, line):
                    errors.append(f'[docs] {rel}:{lineno} {label}：{line.strip()[:90]}')
    if not errors:
        print('[docs] OK  当前文档无旧口径')


def check_sisa(errors):
    scanned = 0
    for base in ('backend', 'algorithm_model', 'src'):
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            dirnames[:] = [d for d in dirnames if d not in ('__pycache__', 'node_modules', 'dist')]
            for name in filenames:
                if os.path.splitext(name)[1] not in ('.py', '.js', '.vue', '.ts'):
                    continue
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, ROOT)
                stem = os.path.splitext(name)[0]
                if stem in FORBIDDEN_MODULES:
                    errors.append(f'[sisa] 禁止模块仍在平台：{rel}')
                try:
                    text = open(path, encoding='utf-8', errors='ignore').read()
                except OSError:
                    continue
                scanned += 1
                for mod in FORBIDDEN_MODULES:
                    if re.search(rf'^\s*(from|import)\s+.*\b{re.escape(mod)}\b', text, re.M):
                        errors.append(f'[sisa] 平台代码仍 import {mod}：{rel}')
                for lineno, line in enumerate(text.splitlines(), 1):
                    if 'MOYU' in line or '墨玉' in line:
                        if any(w in line for w in ('SISA', '不含', '不内置', '不包含', '不进入', '留在', '机密品牌')):
                            continue
                        errors.append(f'[sisa] 平台代码出现墨玉标识：{rel}:{lineno}')

    tracked = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=False).stdout.splitlines()
    for rel in tracked:
        if os.path.splitext(rel)[1].lower() not in CODE_EXT:
            continue
        if rel.startswith('docs/retrospective') or rel.startswith('book/'):
            continue
        if rel == 'scripts/pre_commit_check.py':  # 门禁自身含禁用词字面量
            continue
        try:
            text = open(os.path.join(ROOT, rel), encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if 'MOYU' in line or '墨玉' in line:
                if any(w in line for w in ('SISA', '不含', '不内置', '不包含', '不进入', '留在', '机密品牌')):
                    continue
                errors.append(f'[sisa] 受版本控制的代码/配置出现墨玉标识：{rel}:{lineno}')

    sisa = 'D:/API/SISA'
    print(f'[sisa] 扫描 {scanned} 个代码文件；SISA 目录：{"存在" if os.path.isdir(sisa) else "不可访问（跳过）"}')


def main():
    errors = []
    check_facts(errors)
    check_docs(errors)
    check_sisa(errors)
    if errors:
        print('\nGATE FAIL：')
        for e in errors:
            print(' -', e)
        return 1
    print('GATE PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
