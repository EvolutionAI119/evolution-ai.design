# 结构数一键复核（VALIDATION_REPORT 与门禁的数据源）
import ast, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def collect_facts():
    routes = {}
    for fn in sorted(os.listdir('backend/app/routes')):
        if fn.endswith('.py') and fn != '__init__.py':
            routes[fn] = len(re.findall(
                r'@\w+\.(get|post|put|delete|patch)\s*\(',
                open('backend/app/routes/' + fn, encoding='utf-8').read(),
            ))
    main = open('backend/app/main.py', encoding='utf-8').read()
    db = open('backend/app/database.py', encoding='utf-8').read()
    exp = open('backend/app/routes/export.py', encoding='utf-8').read()
    router = open('src/router.js', encoding='utf-8').read()
    cp = open('algorithm_model/car_modeling/car_params.py', encoding='utf-8').read()
    body = cp.split('class CarParams')[1].split('def ')[0]
    bay = open('backend/app/bayes_optimizer.py', encoding='utf-8').read()

    space_size = None
    for node in ast.walk(ast.parse(bay)):
        targets = node.targets if isinstance(node, ast.Assign) else ([node.target] if isinstance(node, ast.AnnAssign) else [])
        if any(getattr(t, 'id', None) == 'DEFAULT_SPACE' for t in targets):
            if isinstance(node.value, ast.List):
                space_size = len(node.value.elts)

    return routes, {
        'modules': len(routes),
        'routes_total': sum(routes.values()),
        'main_direct': len(re.findall(r'@app\.(get|post)\(', main)),
        'tables': db.count('__tablename__'),
        'formats': len(re.findall(r'"(glb|gltf|stl|obj|iges|step|igs|stp)"', exp)),
        'router_paths': len(re.findall(r'path:', router)),
        'carparams': len(re.findall(r'^\s{4}(\w+)\s*:', body, re.M)),
        'bayes_space': space_size,
    }


def main():
    routes, facts = collect_facts()
    print('| 路由模块 | 端点数 |')
    print('|---|---:|')
    for fn, n in routes.items():
        print(f'| {fn} | {n} |')
    print('routes total =', facts['routes_total'])
    print('main.py direct =', facts['main_direct'])
    print('tables =', facts['tables'])
    print('formats =', facts['formats'])
    print('router paths =', facts['router_paths'])
    print('CarParams fields =', facts['carparams'])
    print('DEFAULT_SPACE =', facts['bayes_space'])
    bay = open('backend/app/bayes_optimizer.py', encoding='utf-8').read()
    for f in ['algorithm_model/car_modeling/continuity_checker.py', 'algorithm_model/surface_quality/continuity.py', 'algorithm_model/surface_quality/grader.py']:
        src = open(f, encoding='utf-8').read()
        for m in re.findall(r'(_DEFAULT_G0_THRESH_MM|_DEFAULT_G1_THRESH_DEG|_DEFAULT_G1_VISUAL_DEG|g1_threshold|g2_threshold)\s*=\s*([\d.]+)', src):
            print(f, m)
    print('converged in bayes:', 'converged' in bay, '| ei_xi:', re.findall(r'ei_xi[^\n]*', bay))


if __name__ == '__main__':
    main()
