"""
综合下载4款失败车的正侧视图：
1. 优先从Wikipedia/Wikimedia Commons获取（无水印、官方图）
2. 备用：Bing图片搜索（关键词含"side profile"+"official"）
"""
import urllib.request, urllib.parse, ssl, re, os, time, json, hashlib
from pathlib import Path

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ROOT = Path(r"d:\API\Evolution-Ai.Design")
OUT_DIR = ROOT / "public" / "_wiki_bing_candidates"
OUT_DIR.mkdir(exist_ok=True)

CARS = [
    {"brand": "bentley", "model": "bentayga", "name": "Bentley Bentayga",
     "wiki_titles": ["Bentley Bentayga", "Bentley_Bentayga"],
     "bing_queries": [
         "Bentley Bentayga side profile official",
         "Bentley Bentayga 2023 side view studio",
         "宾利添越 侧面 官图",
     ]},
    {"brand": "bentley", "model": "flying-spur", "name": "Bentley Flying Spur",
     "wiki_titles": ["Bentley Flying Spur", "Bentley_Flying_Spur"],
     "bing_queries": [
         "Bentley Flying Spur side profile official",
         "Bentley Flying Spur 2020 side view",
         "宾利飞驰 侧面 官图",
     ]},
    {"brand": "bentley", "model": "continental-gtc", "name": "Bentley Continental GTC",
     "wiki_titles": ["Bentley Continental GTC", "Bentley_Continental_GT"],
     "bing_queries": [
         "Bentley Continental GTC side profile official",
         "Bentley Continental GTC convertible side view",
         "宾利欧陆GTC 敞篷 侧面 官图",
     ]},
    {"brand": "rolls-royce", "model": "cullinan", "name": "Rolls-Royce Cullinan",
     "wiki_titles": ["Rolls-Royce Cullinan", "Rolls-Royce_Cullinan"],
     "bing_queries": [
         "Rolls-Royce Cullinan side profile official",
         "Rolls-Royce Cullinan side view studio",
         "劳斯莱斯库里南 侧面 官图",
     ]},
]


def fetch(url, timeout=25, headers=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.read()
        return None
    except Exception as e:
        return None


def fetch_wiki_images(titles, car_dir):
    """从Wikipedia获取图片"""
    imgs = []
    for title in titles:
        # 用REST API获取页面摘要（含缩略图URL）
        api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        print(f"  Wiki API: {api_url}")
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": UA})
            with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            # 原图URL
            original = data.get("originalimage", {}).get("source")
            thumb = data.get("thumbnail", {}).get("source")
            if original:
                # 下载原图
                raw = fetch(original, timeout=30)
                if raw and len(raw) > 20_000:
                    md5 = hashlib.md5(raw).hexdigest()[:8]
                    fname = f"wiki_{md5}.jpg"
                    (car_dir / fname).write_bytes(raw)
                    imgs.append({"file": fname, "source": "wikipedia", "size_kb": round(len(raw)/1024), "url": original})
                    print(f"    Wiki saved {fname} ({len(raw)//1024}KB)")
        except Exception as e:
            print(f"    Wiki ERR: {e}")
        
        # 用API获取页面所有图片
        try:
            api_url2 = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=images&format=json&imlimit=20"
            req = urllib.request.Request(api_url2, headers={"User-Agent": UA})
            with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                for img_info in pdata.get("images", []):
                    img_title = img_info.get("title", "")
                    if not img_title.endswith((".jpg", ".jpeg", ".png")):
                        continue
                    if "logo" in img_title.lower() or "icon" in img_title.lower():
                        continue
                    # 获取图片URL
                    info_url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(img_title)}&prop=imageinfo&iiprop=url|size&format=json"
                    try:
                        req2 = urllib.request.Request(info_url, headers={"User-Agent": UA})
                        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req2, timeout=15) as r2:
                            idata = json.loads(r2.read().decode("utf-8"))
                        ipages = idata.get("query", {}).get("pages", {})
                        for _, ipdata in ipages.items():
                            for ii in ipdata.get("imageinfo", []):
                                url = ii.get("url")
                                w = ii.get("width", 0)
                                h = ii.get("height", 0)
                                if w < 800 or h < 400:
                                    continue
                                raw = fetch(url, timeout=30)
                                if raw and len(raw) > 30_000:
                                    md5 = hashlib.md5(raw).hexdigest()[:8]
                                    ext = url.split(".")[-1].lower()[:4]
                                    fname = f"wiki_{md5}.{ext}"
                                    fpath = car_dir / fname
                                    if not fpath.exists():
                                        fpath.write_bytes(raw)
                                        imgs.append({"file": fname, "source": "wikipedia", 
                                                    "size_kb": round(len(raw)/1024), "url": url,
                                                    "w": w, "h": h})
                                        print(f"    Wiki img {fname} ({w}x{h}, {len(raw)//1024}KB)")
                                    time.sleep(0.2)
                    except Exception as e:
                        pass
        except Exception as e:
            print(f"    Wiki API ERR: {e}")
    return imgs


def fetch_bing_images(query, car_dir, max_imgs=15):
    """从Bing图片搜索获取图片"""
    imgs = []
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1"
    print(f"  Bing: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    Bing ERR: {e}")
        return imgs
    
    # 提取图片URL - Bing的图片URL通常在 murl 参数中
    pattern = r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png))&'
    urls = re.findall(pattern, html)
    # 也尝试其他模式
    pattern2 = r'"murl":"(https?://[^"]+?\.(?:jpg|jpeg|png))"'
    urls.extend(re.findall(pattern2, html))
    pattern3 = r'imgurl=(https?://[^&]+?\.(?:jpg|jpeg|png))'
    urls.extend(re.findall(pattern3, html))
    
    # 去重
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen and "bing.com" not in u and "msn.com" not in u:
            seen.add(u)
            unique_urls.append(u)
    
    print(f"    Bing found {len(unique_urls)} unique URLs")
    
    for img_url in unique_urls[:max_imgs]:
        try:
            req = urllib.request.Request(img_url, headers={"User-Agent": UA, "Referer": "https://www.bing.com/"})
            with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=15) as r:
                raw = r.read()
            if len(raw) < 30_000:
                continue
            md5 = hashlib.md5(raw).hexdigest()[:8]
            ext = img_url.split(".")[-1].lower()[:4] if "." in img_url else "jpg"
            if ext not in ("jpg", "jpeg", "png"):
                ext = "jpg"
            fname = f"bing_{md5}.{ext}"
            fpath = car_dir / fname
            if fpath.exists():
                continue
            fpath.write_bytes(raw)
            imgs.append({"file": fname, "source": "bing", 
                        "size_kb": round(len(raw)/1024), "url": img_url, "query": query})
            print(f"    Bing saved {fname} ({len(raw)//1024}KB)")
            time.sleep(0.2)
        except Exception as e:
            pass
    return imgs


def main():
    all_results = {}
    for car in CARS:
        name = car["name"]
        print(f"\n=== {name} ===")
        car_dir = OUT_DIR / f"{car['brand']}__{car['model']}"
        car_dir.mkdir(exist_ok=True)
        
        all_imgs = []
        # 1. Wikipedia
        print("-- Wikipedia --")
        wiki_imgs = fetch_wiki_images(car["wiki_titles"], car_dir)
        all_imgs.extend(wiki_imgs)
        
        # 2. Bing
        print("-- Bing --")
        for q in car["bing_queries"]:
            bing_imgs = fetch_bing_images(q, car_dir, max_imgs=10)
            all_imgs.extend(bing_imgs)
            time.sleep(1)
        
        all_results[name] = all_imgs
        print(f"  Total: {len(all_imgs)} images")
    
    # 保存日志
    log = OUT_DIR / "_wiki_bing_log.json"
    log.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    
    total = sum(len(v) for v in all_results.values())
    print(f"\n=== 完成 ===")
    print(f"总计: {total} 张图")
    print(f"日志: {log}")


if __name__ == "__main__":
    main()
