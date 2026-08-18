import json, shutil, os
log = json.load(open('scripts/_official_v18_log.json', 'r', encoding='utf-8'))
picks = {}
for c in log:
    imgs = c['images']
    if not imgs: continue
    studio = [i for i in imgs if i.get('bg_type') in ('dark_studio','white_studio') and i.get('w',0)>=600]
    if studio:
        best = max(studio, key=lambda x: x.get('kb',0))
    else:
        big = [i for i in imgs if i.get('w',0)>=600]
        if big: best = max(big, key=lambda x: x.get('w',0))
        else: continue
    picks[c['car']] = best
os.makedirs('public/_v18_picks', exist_ok=True)
items = []
for k, v in picks.items():
    src = 'public/_official_v18/' + k + '/' + v['file']
    dst_name = k.replace('/','_') + '_' + v['file']
    shutil.copy(src, 'public/_v18_picks/' + dst_name)
    print(k + ': ' + v['file'] + ' ' + str(v['w']) + 'x' + str(v['h']) + ' ' + v['bg_type'] + ' ' + str(v['kb']) + 'KB')
    items.append((k, dst_name, v))
html = '<html><head><meta charset="utf-8"><style>body{background:#111;color:#eee;font-family:sans-serif;padding:20px}div{display:inline-block;margin:10px;text-align:center}img{max-width:400px;max-height:200px;object-fit:contain;background:#000;display:block;cursor:pointer}h3{color:#e94560;margin:5px}p{color:#888;font-size:12px}</style></head><body>'
for k, dst_name, v in items:
    html += '<div><h3>' + k + '</h3><img src="/_v18_picks/' + dst_name + '" onclick="window.open(this.src)"><p>' + str(v['w']) + 'x' + str(v['h']) + ' ' + v['bg_type'] + ' ' + str(v['kb']) + 'KB asp=' + str(v['asp']) + '</p></div>'
html += '</body></html>'
open('public/_preview_v18_picks.html', 'w', encoding='utf-8').write(html)
print('picks page done')
