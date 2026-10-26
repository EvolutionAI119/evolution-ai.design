import re
exp = open('backend/app/routes/export.py', encoding='utf-8').read()
m = re.search(r'SUPPORTED_FORMATS\s*=\s*\{(.*?)\}', exp, re.S)
keys = re.findall(r"['\"](\w+)['\"]\s*:", m.group(1))
print('formats dict keys:', len(keys), keys)
bay = open('backend/app/bayes_optimizer.py', encoding='utf-8').read()
ms = re.search(r'DEFAULT_SPACE\s*=\s*\[(.*?)\n\]', bay, re.S)
print('DEFAULT_SPACE items:', len(re.findall(r'\{"name"', ms.group(1))))
for f in ['algorithm_model/surface_quality/grader.py', 'algorithm_model/surface_quality/continuity.py']:
    src = open(f, encoding='utf-8').read()
    print(f, re.findall(r'g\d_threshold[^\d]*([\d.]+)', src))
