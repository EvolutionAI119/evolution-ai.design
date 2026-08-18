import urllib.request, ssl, os, json, hashlib, io
from PIL import Image
CTX = ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
BASE=os.path.dirname(os.path.abspath(__file__)); PUB=os.path.join(BASE,"..","public")
CAND=os.path.join(PUB,"_official_v18")
IDS=["hZhvvgfYC7","N7JhvRVXCK","kBvLoetX3q","iwxLyMLEbD","me2bjdxqGz","BcoabLqmmV","4NlBKuwlL6","3bWtOjzfY9"]

def dl(cdn_id):
    url=f"https://aka.doubaocdn.com/s/{cdn_id}"
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Referer":"https://www.bugatti.com/en/classic-icons/veyron-164"})
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req,timeout=20) as r: return r.read()
    except Exception as e: print(f"  ERR {cdn_id}: {e}"); return None

def an(raw):
    try:
        with Image.open(io.BytesIO(raw)) as im:
            w,h=im.size; md5=hashlib.md5(raw).hexdigest()[:12]; asp=round(w/h,2) if h else 0
            im_s=im.convert("RGB").resize((200,150)); px=list(im_s.getdata()); W,H=200,150
            corners=[(0,0),(W-1,0),(0,H-1),(W-1,H-1),(W//2,0),(W//2,H-1),(0,H//2),(W-1,H//2)]
            cc=[px[y*W+x] for x,y in corners]
            md=max(max(c[i] for c in cc)-min(c[i] for c in cc) for i in range(3))
            dark=sum(1 for r,g,b in px if (r+g+b)/3<50)/len(px)
            light=sum(1 for r,g,b in px if (r+g+b)/3>220)/len(px)
            sky=sum(1 for r,g,b in px if b>150 and b>r+30 and b>g+10)/len(px)
            bg="dark_studio" if md<25 and dark>0.5 else ("white_studio" if md<25 and light>0.5 else ("outdoor" if sky>0.1 else "complex"))
            return {"w":w,"h":h,"asp":asp,"md5":md5,"kb":round(len(raw)/1024),"max_diff":md,"dark":round(dark,3),"light":round(light,3),"sky":round(sky,3),"bg_type":bg}
    except Exception as e: return {"error":str(e)}

car_dir=os.path.join(CAND,"bugatti","veyron"); os.makedirs(car_dir,exist_ok=True)
print("Bugatti Veyron官网图片下载...")
imgs=[]
for i,cid in enumerate(IDS,1):
    print(f"  [{i}] {cid} ...",end=" ")
    raw=dl(cid)
    if raw:
        info=an(raw)
        if "error" not in info:
            fn=f"cand_{i:02d}.jpg"
            with open(os.path.join(car_dir,fn),"wb") as f: f.write(raw)
            imgs.append({"file":fn,"source":f"cdn:{cid}",**info})
            print(f"OK {info['w']}x{info['h']} asp={info['asp']} bg={info['bg_type']} {info['kb']}KB")
        else: print(f"ERR: {info['error']}")
    else: print("FAIL")
print(f"\n共{len(imgs)}张")

# 更新日志
lp=os.path.join(BASE,"_official_v18_log.json")
if os.path.exists(lp):
    with open(lp,"r",encoding="utf-8") as f: log=json.load(f)
    for car in log:
        if car["car"]=="bugatti/veyron":
            car["images"]=imgs; car["total"]=len(imgs); break
    with open(lp,"w",encoding="utf-8") as f: json.dump(log,f,ensure_ascii=False,indent=2)
    # 重新生成预览页
    html='''<!DOCTYPE html><html><head><meta charset="utf-8"><title>官网候选v18</title>
<style>body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
.car-section{margin-bottom:30px;background:#16213e;border-radius:10px;padding:15px}
.car-title{color:#e94560;font-size:18px;font-weight:bold;margin-bottom:5px}
.car-source{color:#888;font-size:11px;margin-bottom:10px;word-break:break-all}
.cand-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.cand-card{background:#0f0f1e;border:2px solid #333;border-radius:8px;overflow:hidden;cursor:pointer}
.cand-card:hover{border-color:#e94560}
.cand-card img{width:100%;height:180px;object-fit:contain;background:#000;display:block}
.cand-label{padding:6px 8px;font-size:11px;color:#aaa}
.tag{display:inline-block;padding:2px 6px;border-radius:3px;font-size:10px;margin-right:3px}
.tag.ok{background:#2ecc71;color:#000}.tag.bad{background:#e94560;color:#fff}</style></head><body>
<div id="root"></div><script>const DATA='''+json.dumps(log,ensure_ascii=False)+''';
const root=document.getElementById('root');
DATA.forEach(car=>{const sec=document.createElement('div');sec.className='car-section';
const t=document.createElement('div');t.className='car-title';t.textContent=car.name+' ('+car.total+'张)';sec.appendChild(t);
const src=document.createElement('div');src.className='car-source';src.textContent='官网: '+car.official_page;sec.appendChild(src);
const g=document.createElement('div');g.className='cand-grid';
car.images.forEach(c=>{const card=document.createElement('div');card.className='cand-card';
const img=document.createElement('img');const p='/_official_v18/'+car.car+'/'+c.file;img.src=p;img.loading='lazy';
img.onclick=()=>window.open(p,'_blank');img.onerror=()=>{img.style.display='none'};card.appendChild(img);
const l=document.createElement('div');l.className='cand-label';
const ao=c.asp>=1.2&&c.asp<=2.5;const bo=c.bg_type==='dark_studio'||c.bg_type==='white_studio';
l.innerHTML=`${c.file} ${c.w}x${c.h} ${c.kb}KB <span class="tag ${ao?'ok':'bad'}">asp=${c.asp}</span><span class="tag ${bo?'ok':'bad'}">${c.bg_type}</span>`;
card.appendChild(l);g.appendChild(card)});sec.appendChild(g);root.appendChild(sec)});</script></body></html>'''
    with open(os.path.join(PUB,"_preview_official_v18.html"),"w",encoding="utf-8") as f: f.write(html)
    print("预览页已更新")
