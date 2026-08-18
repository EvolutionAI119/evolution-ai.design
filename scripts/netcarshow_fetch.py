"""
从 NetCarShow.com 批量下载4款失败车的Side Profile正侧视图
NetCarShow URL格式：https://www.netcarshow.com/<brand>-<model>[-<year>]/
图片URL通常为：https://www.netcarshow.com/image[-cc]/<brand>-<model>-<year>-<id>-<seq>.jpg
"""
import urllib.request, urllib.parse, ssl, re, os, time, hashlib
from pathlib import Path

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ROOT = Path(r"d:\API\Evolution-Ai.Design")
OUT_DIR = ROOT / "public" / "_netcarshow_candidates"
OUT_DIR.mkdir(exist_ok=True)

# 4款失败车（注意：Continental GTC已用其他图替换过，但仍是失败的）
# NetCarShow URL需要特殊处理：品牌小写，空格用下划线
CARS = [
    {
        "brand": "bentley", "model": "bentayga",
        "name": "Bentley Bentayga",
        "urls": [
            "https://www.netcarshow.com/bentley-bentayga/",
            "https://www.netcarshow.com/bentley-bentayga-2023/",
            "https://www.netcarshow.com/bentley-bentayga-2022/",
            "https://www.netcarshow.com/bentley-bentayga-2021/",
            "https://www.netcarshow.com/bentley-bentayga-2020/",
            "https://www.netcarshow.com/bentley-bentayga-2018/",
        ],
    },
    {
        "brand": "bentley", "model": "flying-spur",
        "name": "Bentley Flying Spur",
        "urls": [
            "https://www.netcarshow.com/bentley-flying_spur/",
            "https://www.netcarshow.com/bentley-flying_spur-2024/",
            "https://www.netcarshow.com/bentley-flying_spur-2023/",
            "https://www.netcarshow.com/bentley-flying_spur-2020/",
            "https://www.netcarshow.com/bentley-flying_spur-2014/",
        ],
    },
    {
        "brand": "bentley", "model": "continental-gtc",
        "name": "Bentley Continental GTC",
        "urls": [
            "https://www.netcarshow.com/bentley-continental_gt-2019/",
            "https://www.netcarshow.com/bentley-continental_gtc-2019/",
            "https://www.netcarshow.com/bentley-continental_gt-2018/",
            "https://www.netcarshow.com/bentley-continental_gt-2017/",
            "https://www.netcarshow.com/bentley-continental_gt_speed-2018/",
        ],
    },
    {
        "brand": "rolls-royce", "model": "cullinan",
        "name": "Rolls-Royce Cullinan",
        "urls": [
            "https://www.netcarshow.com/rolls-royce-cullinan/",
            "https://www.netcarshow.com/rolls-royce-cullinan-2023/",
            "https://www.netcarshow.com/rolls-royce-cullinan-2022/",
            "https://www.netcarshow.com/rolls-royce-cullinan-2020/",
            "https://www.netcarshow.com/rolls-royce-cullinan-2019/",
        ],
    },
]


def fetch(url, timeout=25):
    """获取URL内容，返回bytes"""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*;q=0.8,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  ERR {url}: {e}")
        return None


def extract_image_urls(html_text, page_url):
    """从HTML中提取NetCarShow的图片URL"""
    urls = set()
    # NetCarShow图片URL模式
    patterns = [
        r'image-cc/[a-z0-9_\-]+\.jpg',
        r'image/[a-z0-9_\-]+\.jpg',
        r'wallpaper-[a-z0-9_\-]+\.jpg',
        r"['\"]([^'\"]*?image[^'\"]*?\.jpg)['\"]",
        r"['\"]([^'\"]*?\.jpg)['\"]",
    ]
    for p in patterns:
        for m in re.finditer(p, html_text, re.IGNORECASE):
            u = m.group(1) if m.lastindex else m.group(0)
            if not u.startswith("http"):
                u = urllib.parse.urljoin(page_url, u)
            if "netcarshow.com" in u or u.endswith(".jpg"):
                urls.add(u)
    return list(urls)


def download_car(car):
    """下载一款车的所有候选图"""
    name = car["name"]
    print(f"\n=== {name} ===")
    
    car_dir = OUT_DIR / f"{car['brand']}__{car['model']}"
    car_dir.mkdir(exist_ok=True)
    
    all_imgs = []
    successful_pages = 0
    
    for page_url in car["urls"]:
        print(f"  Fetching: {page_url}")
        raw = fetch(page_url, timeout=20)
        if not raw:
            continue
        try:
            html = raw.decode("utf-8", errors="ignore")
        except:
            continue
        
        if "404" in html[:500] or "not found" in html[:500].lower():
            print(f"    404 not found")
            continue
        
        successful_pages += 1
        img_urls = extract_image_urls(html, page_url)
        print(f"    Found {len(img_urls)} image URLs")
        
        # 下载每张图
        for img_url in img_urls[:30]:  # 每个页面最多30张
            if "thumb" in img_url.lower() or "icon" in img_url.lower():
                continue
            img_data = fetch(img_url, timeout=30)
            if not img_data or len(img_data) < 20_000:
                continue
            md5 = hashlib.md5(img_data).hexdigest()[:8]
            fname = f"{md5}.jpg"
            fpath = car_dir / fname
            if fpath.exists():
                continue
            fpath.write_bytes(img_data)
            all_imgs.append({
                "file": fname,
                "source_url": img_url,
                "page_url": page_url,
                "size_kb": round(len(img_data) / 1024),
                "md5": md5,
            })
            print(f"    Saved {fname} ({len(img_data)//1024}KB) from {img_url.split('/')[-1]}")
            time.sleep(0.3)  # 礼貌延迟
    
    print(f"  {name}: {successful_pages} pages OK, {len(all_imgs)} images downloaded")
    return all_imgs


# 主流程
import json
results = {}
for car in CARS:
    imgs = download_car(car)
    results[car["name"]] = imgs

# 保存日志
log_path = OUT_DIR / "_netcarshow_log.json"
log_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

total = sum(len(v) for v in results.values())
print(f"\n=== 完成 ===")
print(f"总计下载: {total} 张图")
print(f"日志: {log_path}")
print(f"目录: {OUT_DIR}")
