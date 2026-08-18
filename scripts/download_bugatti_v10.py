#!/usr/bin/env python3
"""
v10: 从 Bugatti newsroom 下载 3 款车的正侧视官图

方法论：
1. 仅访问 https://newsroom.bugatti.com/models/{model}
2. 从 HTML 中提取所有 bugatti-newsroom.imgix.net 的图片 URL
   - 注意：文件名可能含空格（如 "01 2510 BUGATTI-...jpg"），正则要允许空格
   - 注意：og:image 等可能用 path-based 参数（_,w_1200,h_630），需剥离
   - 注意：HTML 属性中 & 用 &amp; 表示，需 unescape
3. 排除改装/错误变体（profilee / chiron-sport / chiron-pur / chiron-super /
   centodieci / la-voiture / mistral / bolide / tourbillon / brouillard）
4. 对每个候选 URL，用 imgix 缩放参数 ?w=1920&h=1080&fit=crop 下载较小版本
   （原图 8-12MB，太大；用 imgix 缩放可显著减小体积用于筛选）
5. 由于 fit=crop 会把所有图都裁成 1920x1080（比例恒为 1.78），无法直接判断
   原始宽高比；因此额外用 ?w=400（仅限宽，保持比例）下载一张小图，
   用 PIL 读取其宽高，得到原始宽高比
6. 选择原始宽高比最接近 1.8（侧视图典型比例）的候选
7. 下载最佳候选的原图（不加任何缩放参数）保存到
   d:\\API\\Evolution-Ai.Design\\public\\brands\\bugatti\\{model}.jpg
8. 日志保存到 d:\\API\\Evolution-Ai.Design\\scripts\\_bugatti_v10_log.json

注意：
- Divo 车型特别排除 Chiron Profilee（这是之前的错误）
- User-Agent: Mozilla/5.0
- SSL 验证关闭
- 超时 30 秒
"""
import os
import re
import json
import time
import hashlib
import ssl
import io
import html as html_mod
import urllib.request
import urllib.parse
from pathlib import Path

# === 配置 ===
BASE_DIR = Path(r"d:\API\Evolution-Ai.Design\public\brands\bugatti")
LOG_PATH = Path(r"d:\API\Evolution-Ai.Design\scripts\_bugatti_v10_log.json")
TIMEOUT = 30
UA = "Mozilla/5.0"

# 3 款车型
MODELS = ["chiron", "veyron", "divo"]

# 排除变体（URL 中出现这些关键词的图片一律排除）
# Divo 车型特别要排除 Chiron Profilee（之前的错误）
EXCLUDE_KEYWORDS = [
    "profilee",
    "chiron-sport",
    "chiron-pur",
    "chiron-super",
    "centodieci",
    "la-voiture",
    "mistral",
    "bolide",
    "tourbillon",
    "brouillard",
]

# imgix CDN 域名
IMGIX_HOST = "bugatti-newsroom.imgix.net"

# 侧视图目标宽高比
TARGET_ASPECT = 1.8

# 非图片扩展名（直接跳过，不尝试下载，节省时间）
NON_IMAGE_EXTS = (
    ".pdf", ".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v",
    ".mp3", ".wav", ".flac", ".aac",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".7z", ".tar", ".gz",
)


def has_non_image_ext(url: str) -> bool:
    """URL 路径是否以非图片扩展名结尾"""
    path = url.split("?")[0].lower().rstrip("/")
    return any(path.endswith(ext) for ext in NON_IMAGE_EXTS)


def clean_url(u: str) -> str:
    """清理 URL 中的控制字符和首尾空白"""
    u = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", u)
    return u.strip()


def make_ssl_context() -> ssl.SSLContext:
    """创建不校验证书的 SSL 上下文"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def encode_url_path(url: str) -> str:
    """对 URL 的 path 部分做百分号编码（处理空格等特殊字符），保留 / 和已知安全字符"""
    try:
        parts = urllib.parse.urlsplit(url)
        # quote path but keep / and common safe chars
        encoded_path = urllib.parse.quote(parts.path, safe="/%:@!$&'()*+,;=-._~")
        return urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, encoded_path, parts.query, parts.fragment)
        )
    except Exception:
        return url


def fetch_html(url: str):
    """获取页面 HTML，返回 (html, final_url, error)"""
    url = clean_url(url)
    ctx = make_ssl_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            data = resp.read()
            enc = resp.headers.get_content_charset() or "utf-8"
            try:
                text = data.decode(enc, errors="replace")
            except Exception:
                text = data.decode("utf-8", errors="replace")
            return text, resp.url, None
    except Exception as e:
        return None, url, str(e)


def normalize_imgix_url(raw: str) -> str:
    """
    将原始 imgix URL 归一化为干净的基础 URL：
    - HTML unescape（&amp; -> &）
    - 剥离 path-based 参数（_,w_1200,h_630 等）
    - 剥离 query string
    - 去掉末尾多余标点
    """
    url = html_mod.unescape(raw).strip()
    url = re.sub(r"[,\s\)\]\}]+$", "", url)
    # 剥离 path-based imgix 参数: /ID_,w_X,h_Y/file -> /ID/file
    url = re.sub(r"_,[^/]+", "", url)
    # 剥离 query string
    url = url.split("?")[0]
    return url


def extract_imgix_urls(html_text: str):
    """
    从 HTML 中提取所有 bugatti-newsroom.imgix.net 的图片 URL。

    关键：文件名可能含空格（如 "01 2510 BUGATTI-Broward-...jpg"），
    因此正则不能排除空格；URL 通常出现在引号内，所以匹配到引号为止。
    """
    if not html_text:
        return []
    # 匹配到双引号、单引号、尖括号、反斜杠为止（允许空格、分号等）
    pattern = r'https?://bugatti-newsroom\.imgix\.net/[^"\'<>\\]+'
    raw_urls = re.findall(pattern, html_text, re.I)

    seen = set()
    unique = []
    for u in raw_urls:
        url = normalize_imgix_url(u)
        if url and url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def is_excluded(url_lower: str):
    """检查 URL 是否命中排除关键词，返回命中的关键词或 None"""
    for kw in EXCLUDE_KEYWORDS:
        if kw in url_lower:
            return kw
    return None


def download_image(url: str):
    """下载图片，返回 (data, error)"""
    url = clean_url(url)
    url = encode_url_path(url)
    ctx = make_ssl_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            data = resp.read()
            if len(data) < 5000:
                return None, "too_small(<5KB)"
            # 校验是 JPEG / PNG / WEBP
            if (
                data[:2] == b"\xff\xd8"
                or data[:4] == b"\x89PNG"
                or data[:4] == b"RIFF"
            ):
                return data, None
            return None, f"not_image:head={data[:4].hex()}"
    except Exception as e:
        return None, str(e)


def get_image_size(data):
    """用 PIL 从图片数据读取宽高"""
    if not data:
        return 0, 0
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        return img.size
    except Exception:
        return 0, 0


def append_imgix_params(url: str, params: str) -> str:
    """给干净的基础 URL 追加 imgix 查询参数"""
    base = url.split("?")[0]
    return f"{base}?{params}"


def process_model(model: str):
    """处理一款车型"""
    print(f"\n{'=' * 60}")
    print(f"处理: bugatti/{model}")
    print(f"{'=' * 60}")

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    save_path = BASE_DIR / f"{model}.jpg"

    page_url = f"https://newsroom.bugatti.com/models/{model}"
    print(f"\n  访问: {page_url}")
    html_text, _final_url, err = fetch_html(page_url)
    if err:
        print(f"    失败: {err}")
        return {
            "model": model,
            "status": f"fetch_failed:{err}",
            "page_url": page_url,
            "candidates": [],
        }

    print(f"    HTML 长度: {len(html_text)} 字符")

    # 提取 imgix URL（已归一化：剥离 path params 和 query params）
    img_urls = extract_imgix_urls(html_text)
    print(f"    提取到 {len(img_urls)} 个归一化 imgix URL")

    # 过滤排除变体 + 非图片扩展名
    filtered = []
    for u in img_urls:
        low = u.lower()
        ex = is_excluded(low)
        if ex:
            print(f"    排除({ex}): {u[:100]}")
            continue
        if has_non_image_ext(low):
            print(f"    排除(非图片): {u[:100]}")
            continue
        filtered.append(u)

    print(f"    过滤后剩余 {len(filtered)} 个候选")
    # 打印所有候选的完整 URL（用于调试）
    for i, u in enumerate(filtered):
        print(f"      候选[{i + 1}] {u}")

    if not filtered:
        return {
            "model": model,
            "status": "no_candidates_after_filter",
            "page_url": page_url,
            "candidates": [],
        }

    # 对每个候选下载小版本以确定宽高比
    candidates = []
    for i, img_url in enumerate(filtered):
        # 任务要求的缩放参数（用于下载较小版本）
        small_url = append_imgix_params(img_url, "w=1920&h=1080&fit=crop")
        # 额外用 ?w=400 保持原始宽高比，用于判定侧视图比例
        asp_url = append_imgix_params(img_url, "w=400")

        print(f"\n  [{i + 1}/{len(filtered)}] {img_url[:120]}")

        # 1) 下载保持比例的小图，确定原始宽高比
        asp_data, asp_err = download_image(asp_url)
        if asp_data is None:
            print(f"    比例探测失败: {asp_err}")
            continue
        aw, ah = get_image_size(asp_data)
        if aw == 0 or ah == 0:
            print(f"    无法读取尺寸，跳过")
            continue
        asp = aw / ah
        print(f"    原始比例探测: {aw}x{ah} = {asp:.3f}")

        # 2) 下载任务要求的小版本（fit=crop, 1920x1080）
        small_data, small_err = download_image(small_url)
        if small_data is None:
            print(f"    小版本下载失败: {small_err}，跳过")
            continue
        sw, sh = get_image_size(small_data)
        small_kb = len(small_data) // 1024
        print(f"    小版本: {sw}x{sh} {small_kb}KB")

        candidates.append(
            {
                "url": img_url,
                "orig_w": aw,
                "orig_h": ah,
                "asp": round(asp, 3),
                "asp_diff_to_1_8": round(abs(asp - TARGET_ASPECT), 3),
                "small_w": sw,
                "small_h": sh,
                "small_kb": small_kb,
            }
        )

    if not candidates:
        return {
            "model": model,
            "status": "no_valid_candidates",
            "page_url": page_url,
            "candidates": [],
        }

    # 按原始宽高比与 1.8 的差距升序排序
    candidates.sort(key=lambda c: c["asp_diff_to_1_8"])

    print(f"\n  候选排序（按宽高比接近 {TARGET_ASPECT}）:")
    for c in candidates[:10]:
        print(
            f"    asp={c['asp']:<6} diff={c['asp_diff_to_1_8']:<5} "
            f"small={c['small_w']}x{c['small_h']} {c['small_kb']}KB  {c['url'][:80]}"
        )

    best = candidates[0]
    print(f"\n  最佳候选: {best['url']}")
    print(f"    原始比例: {best['orig_w']}x{best['orig_h']} = {best['asp']}")

    # 下载最佳候选的原图（不加任何缩放参数）
    print(f"    下载原图 ...")
    orig_data, orig_err = download_image(best["url"])
    if orig_data is None:
        print(f"    原图下载失败: {orig_err}")
        return {
            "model": model,
            "status": f"orig_download_failed:{orig_err}",
            "page_url": page_url,
            "best": best,
            "candidates": candidates[:10],
        }

    ow, oh = get_image_size(orig_data)
    okb = len(orig_data) // 1024
    md5 = hashlib.md5(orig_data).hexdigest()[:12]
    print(f"    原图: {ow}x{oh} {okb}KB MD5={md5}")

    with open(save_path, "wb") as f:
        f.write(orig_data)
    print(f"    已保存: {save_path}")

    return {
        "model": model,
        "status": "ok",
        "page_url": page_url,
        "url": best["url"],
        "w": ow,
        "h": oh,
        "asp": round(ow / oh, 3) if oh else 0,
        "kb": okb,
        "md5": md5,
        "save_path": str(save_path),
        "best": best,
        "all_candidates": candidates[:10],
    }


def main():
    print("=" * 60)
    print("v10 Bugatti newsroom 正侧视官图下载器")
    print(f"目标车型: {MODELS}")
    print(f"排除关键词: {EXCLUDE_KEYWORDS}")
    print("=" * 60)

    results = []
    for model in MODELS:
        try:
            result = process_model(model)
        except Exception as e:
            import traceback

            print(f"\n  异常: {e}")
            traceback.print_exc()
            result = {
                "model": model,
                "status": f"error:{e}",
                "candidates": [],
            }
        results.append(result)
        # 实时保存日志，防止中途崩溃丢失
        LOG_PATH.write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        time.sleep(2)  # 礼貌延迟

    LOG_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n\n{'=' * 60}")
    print(f"日志已保存: {LOG_PATH}")

    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"\n汇总: {ok}/{len(MODELS)} 成功")
    for r in results:
        if r.get("status") == "ok":
            print(
                f"  [OK]   {r['model']}: {r['w']}x{r['h']} "
                f"asp={r['asp']} {r['kb']}KB  {r['url'][:70]}"
            )
        else:
            print(f"  [FAIL] {r['model']}: {r.get('status')}")


if __name__ == "__main__":
    main()
