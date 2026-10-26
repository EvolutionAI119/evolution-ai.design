# 结构数一键复核（VALIDATION_REPORT 数据源）
import re, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

total = 0
print('| 路由模块 | 端点数 |')
print('|---|---:|')
for fn in sorted(os.listdir('backend/app/routes')):
    if fn.endswith('.py') and fn != '__init__.py':
        n = len(re.findall(r'@\w+\.(get|post|put|delete|patch)\s*\(', open('backend/app/routes/' + fn, encoding='utf-8').read()))
        print(f'| {fn} | {n} |')
        total += n
print('routes total =', total)
main = open('backend/app/main.py', encoding='utf-8').read()
print('main.py direct =', len(re.findall(r'@app\.(get|post)\(', main)))
db = open('backend/app/database.py', encoding='utf-8').read()
print('tables =', db.count('__tablename__'))
exp = open('backend/app/routes/export.py', encoding='utf-8').read()
print('formats =', len(re.findall(r'"(glb|gltf|stl|obj|iges|step|igs|stp)"', exp)))
r = open('src/router.js', encoding='utf-8').read()
print('router paths =', len(re.findall(r'path:', r)))
cp = open('algorithm_model/car_modeling/car_params.py', encoding='utf-8').read()
body = cp.split('class CarParams')[1].split('def ')[0]
print('CarParams fields =', len(re.findall(r'^\s{4}(\w+)\s*:', body, re.M)))
bay = open('backend/app/bayes_optimizer.py', encoding='utf-8').read()
print('DEFAULT_SPACE =', bay.count('{"name"'))
for f in ['algorithm_model/car_modeling/continuity_checker.py', 'algorithm_model/surface_quality/continuity.py', 'algorithm_model/surface_quality/grader.py']:
    src = open(f, encoding='utf-8').read()
    for m in re.findall(r'(_DEFAULT_G0_THRESH_MM|_DEFAULT_G1_THRESH_DEG|_DEFAULT_G1_VISUAL_DEG|g1_threshold|g2_threshold)\s*=\s*([\d.]+)', src):
        print(f, m)
print('converged in bayes:', 'converged' in bay, '| ei_xi:', re.findall(r'ei_xi[^\n]*', bay))
