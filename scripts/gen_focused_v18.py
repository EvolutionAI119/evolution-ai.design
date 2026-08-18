import json, os
BASE=os.path.dirname(os.path.abspath(__file__)); PUB=os.path.join(BASE,"..","public")
lp=os.path.join(BASE,"_official_v18_log.json")
with open(lp,"r",encoding="utf-8") as f: log=json.load(f)

# 筛选: width>=600 的候选图
focused=[]
for car in log:
    big_imgs=[c for c in car["images"] if c.get("w",0)>=600]
    if big_imgs:
        focused.append({"car":car["car"],"name":car["name"],"official_page":car["official_page"],
                        "total":len(big_imgs),"images":big_imgs})

html='''<!DOCTYPE html><html><head><meta charset="utf-8"><title>聚焦验证v18</title>
<style>body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center}.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{margin-bottom:30px;background:#16213e;border-radius:10px;padding:15px}
.car-title{color:#e94560;font-size:18px;font-weight:bold;margin-bottom:5px}
.car-source{color:#888;font-size:11px;margin-bottom:10px;word-break:break-all}
.cand-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:10px}
.cand-card{background:#0f0f1e;border:2px solid #333;border-radius:8px;overflow:hidden;cursor:pointer}
.cand-card:hover{border-color:#e94560}
.cand-card img{width:100%;height:200px;object-fit:contain;background:#000;display:block}
.cand-label{padding:6px 8px;font-size:11px;color:#aaa}
.tag{display:inline-block;padding:2px 6px;border-radius:3px;font-size:10px;margin-right:3px}
.tag.ok{background:#2ecc71;color:#000}.tag.bad{background:#e94560;color:#fff}
</style></head><body>
<h1>聚焦验证 - 仅width≥600px的官网候选图</h1>
<div class="sub">标准：正侧视(90°)+纯净背景+车型正确+无水印+非改装 | 点击放大</div>
<div id="root"></div><script>const DATA='''+json.dumps(focused,ensure_ascii=False)+''';
const root=document.getElementById('root');
DATA.forEach(car=>{const sec=document.createElement('div');sec.className='car-section';
const t=document.createElement('div');t.className='car-title';t.textContent=car.name+' ('+car.total+'张大图)';sec.appendChild(t);
const src=document.createElement('div');src.className='car-source';src.textContent='官网: '+car.official_page;sec.appendChild(src);
const g=document.createElement('div');g.className='cand-grid';
car.images.forEach(c=>{const card=document.createElement('div');card.className='cand-card';
const img=document.createElement('img');const p='/_official_v18/'+car.car+'/'+c.file;img.src=p;img.loading='lazy';
img.onclick=()=>window.open(p,'_blank');img.onerror=()=>{img.style.display='none'};card.appendChild(img);
const l=document.createElement('div');l.className='cand-label';
const ao=c.asp>=1.2&&c.asp<=2.5;const bo=c.bg_type==='dark_studio'||c.bg_type==='white_studio';
l.innerHTML=`${c.file} ${c.w}x${c.h} ${c.kb}KB <span class="tag ${ao?'ok':'bad'}">asp=${c.asp}</span><span class="tag ${bo?'ok':'bad'}">${c.bg_type}</span>`;
card.appendChild(l);g.appendChild(card)});sec.appendChild(g);root.appendChild(sec)});</script></body></html>'''
with open(os.path.join(PUB,"_preview_focused_v18.html"),"w",encoding="utf-8") as f: f.write(html)
print(f"聚焦预览页已生成: {len(focused)}款车")
for c in focused: print(f"  {c['name']}: {c['total']}张大图")
