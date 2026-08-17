"""
车型图片筛选流水线 - 全流程自动化回归测试 CLI（19款车 × 38用例）
===================================================================

数据集：public/brands/ 下的品牌正侧视图片（19款车，每款原图+翻转图 = 38用例）。

核心验证维度：
  A. 方向判定核心能力（必须100%，算法产出质量指标）
     原图→期望left，翻转图→期望right，flip_needed必须与方向逻辑一致
  B. 图片合规度基线（参考指标，反映品牌图当前质量）
     纯白背景过滤 + 完整车身检测（含自动白边填充）

=== 命令行快速上手 ===

# 【默认】运行19款车全量回归 + 生成HTML报告
python scripts/test_pipeline_e2e.py

# 仅测试指定车型（格式 brand/model，多个用空格分隔）
python scripts/test_pipeline_e2e.py --car porsche/911
python scripts/test_pipeline_e2e.py --car bentley/bentayga bugatti/chiron

# 仅测试指定品牌
python scripts/test_pipeline_e2e.py --brand ferrari
python scripts/test_pipeline_e2e.py --brand porsche bugatti

# 快速模式：只跑A类方向判定（跳过B类+HTML，最快3秒出结果）
python scripts/test_pipeline_e2e.py --quick

# 不生成HTML（只跑+输出汇总）
python scripts/test_pipeline_e2e.py --no-html

# 自定义HTML输出路径（默认 public/_test_pipeline_e2e_report.html）
python scripts/test_pipeline_e2e.py --html-out D:/reports/pipeline.html

# 不内联预览图（HTML小10倍，图片通过URL加载，需本地服务器）
python scripts/test_pipeline_e2e.py --no-inline-img

# 详细模式：逐用例打印完整指标
python scripts/test_pipeline_e2e.py --verbose

# 严格模式：除A类外，B类合规度也必须100%（用作基线回归）
python scripts/test_pipeline_e2e.py --strict
"""
import argparse, sys, hashlib, base64, io, json
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import (
    analyze_background, WHITE_BG_CONFIG,
    detect_complete_car, COMPLETE_CAR_CONFIG,
    detect_car_direction, DIRECTION_CONFIG,
    _auto_pad_white,
)

ROOT = Path(__file__).resolve().parent.parent

# 19款车完整列表（与主流水线 CARS 保持一致）
ALL_CARS = [
    {"brand": "bentley", "model": "bentayga"},
    {"brand": "bentley", "model": "flying-spur"},
    {"brand": "bentley", "model": "continental-gtc"},
    {"brand": "bentley", "model": "continental-gt"},
    {"brand": "rolls-royce", "model": "cullinan"},
    {"brand": "rolls-royce", "model": "phantom"},
    {"brand": "rolls-royce", "model": "ghost"},
    {"brand": "rolls-royce", "model": "wraith"},
    {"brand": "ferrari", "model": "f8-tributo"},
    {"brand": "ferrari", "model": "sf90"},
    {"brand": "ferrari", "model": "roma"},
    {"brand": "porsche", "model": "911"},
    {"brand": "porsche", "model": "taycan"},
    {"brand": "porsche", "model": "macan"},
    {"brand": "porsche", "model": "cayenne"},
    {"brand": "porsche", "model": "panamera"},
    {"brand": "bugatti", "model": "divo"},
    {"brand": "bugatti", "model": "veyron"},
    {"brand": "bugatti", "model": "chiron"},
]


def build_arg_parser():
    """构造命令行参数解析器"""
    p = argparse.ArgumentParser(
        description="车型图片筛选流水线 - 全流程自动化回归测试（19款车 × 38用例）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 全量回归 + HTML报告（默认行为）
  python test_pipeline_e2e.py

  # 单车型
  python test_pipeline_e2e.py --car porsche/911

  # 快速模式（只跑A类方向判定，无HTML）
  python test_pipeline_e2e.py --quick
        """,
    )
    # 车型选择
    p.add_argument("--car", "-c", nargs="+",
                   help="只测试指定车型（格式 brand/model，可多个，如 porsche/911 bentley/bentayga）")
    p.add_argument("--brand", "-b", nargs="+",
                   help="只测试指定品牌（可多个，如 porsche ferrari）")
    # 运行模式
    p.add_argument("--quick", "-q", action="store_true",
                   help="快速模式：只跑A类方向判定（跳过B类+MD5+HTML+分辨率），速度最快")
    p.add_argument("--strict", action="store_true",
                   help="严格模式：除A类外，B类合规度也必须100%%才返回退出码0")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="详细模式：逐用例打印完整检测指标")
    # 报告
    p.add_argument("--no-html", action="store_true",
                   help="不生成HTML报告（仅控制台输出）")
    p.add_argument("--html-out", type=str, default=None,
                   help="自定义HTML报告输出路径（默认: public/_test_pipeline_e2e_report.html）")
    p.add_argument("--no-inline-img", action="store_true",
                   help="HTML中不内联图片（文件小10倍，图片通过/brands URL加载，需本地服务器）")
    p.add_argument("--json-out", type=str, default=None,
                   help="额外导出JSON格式机器可读报告（用于CI集成）")
    return p


def select_cars(args):
    """根据 --car/--brand 参数筛选待测试车型列表"""
    cars = list(ALL_CARS)
    if args.brand:
        brand_set = set(b.lower() for b in args.brand)
        cars = [c for c in cars if c["brand"].lower() in brand_set]
        print(f"[筛选] 按品牌过滤 → 选中 {len(cars)} 款车: {', '.join(c['brand']+'/'+c['model'] for c in cars)}")
    if args.car:
        keep = []
        wanted = set()
        for raw in args.car:
            parts = raw.lower().replace("\\", "/").split("/")
            if len(parts) == 2:
                wanted.add((parts[0], parts[1]))
            else:
                print(f"⚠️  跳过非法格式 --car {raw} （期望 brand/model）")
        keep = [c for c in cars if (c["brand"].lower(), c["model"].lower()) in wanted]
        missing = wanted - {(c["brand"].lower(), c["model"].lower()) for c in keep}
        if missing:
            print(f"⚠️  以下车型不存在于配置: {', '.join('/'.join(x) for x in missing)}")
        cars = keep
        print(f"[筛选] 按车型过滤 → 选中 {len(cars)} 款车: {', '.join(c['brand']+'/'+c['model'] for c in cars)}")
    return cars


def img_to_dataurl(arr):
    """numpy array -> base64 data url (用于HTML内联预览)"""
    im = Image.fromarray(arr)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def file_md5(path):
    """文件MD5（用于验证19张图唯一）"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_one_case(img_path, expected_direction, arr_override=None, quick=False):
    """
    对单张图执行测试。
    参数:
      expected_direction: 'left'（原图）或 'right'（翻转图）
      arr_override: 可选，覆盖图片数组（用于翻转图）
      quick:        True=只跑A类方向判定（跳过B类合规度）
    返回: dict with step results
    """
    with Image.open(img_path) as im:
        arr = np.array(im.convert("RGB"))
    if arr_override is not None:
        arr = arr_override

    if not quick:
        # B类：纯白背景过滤
        step1 = analyze_background(arr, WHITE_BG_CONFIG)
        # B类：完整车身检测（含自动白边填充）
        step2 = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
        padded = False
        if not step2["pass"] and COMPLETE_CAR_CONFIG.get("auto_pad_white", False):
            arr_padded, did_pad = _auto_pad_white(arr, COMPLETE_CAR_CONFIG)
            if did_pad:
                step2_padded = detect_complete_car(arr_padded, COMPLETE_CAR_CONFIG)
                if step2_padded["pass"]:
                    step2 = step2_padded
                    padded = True
                    arr = arr_padded
    else:
        step1 = {"pass": None, "white_ratio": 0, "brightness": 0, "reasons": ["SKIP(quick)"]}
        step2 = {"pass": None, "width_ratio": 0, "height_ratio": 0, "reasons": ["SKIP(quick)"]}
        padded = False

    # A类：车头方向自动判定
    step3 = detect_car_direction(arr, DIRECTION_CONFIG)
    dir_match = step3["direction"] == expected_direction

    # flip_needed 一致性检查：车头非left时 flip_needed应为True
    flip_logic_correct = (step3["direction"] == "left") == (not step3["flip_needed"])

    # 方向判定核心能力（A类，主指标）
    direction_pass = dir_match and flip_logic_correct
    # 图片合规度（B类，参考指标）
    compliance_pass = bool(step1["pass"] and step2["pass"]) if not quick else None

    return {
        "step1_white": step1,
        "step2_complete": step2,
        "step2_padded": padded,
        "step3_direction": step3,
        "dir_match": dir_match,
        "flip_logic_correct": flip_logic_correct,
        "direction_pass": direction_pass,   # A类：方向判定核心能力
        "compliance_pass": compliance_pass, # B类：图片合规度基线（参考）；quick时为None
        "arr_for_preview": arr,
    }


def main(cli_args=None):
    args = build_arg_parser().parse_args(cli_args)
    cars_to_test = select_cars(args)
    if not cars_to_test:
        print("❌ 没有要测试的车型（--car/--brand 筛选后为空），直接退出")
        return 2

    # quick模式自动关闭HTML（节省时间）
    generate_html = (not args.no_html) and (not args.quick)
    # quick模式跳过分辨率/MD5
    do_baseline = not args.quick

    tag_quick = "[快速模式] " if args.quick else ""
    tag_strict = "[严格模式] " if args.strict else ""
    print("=" * 90)
    print(f"  {tag_quick}{tag_strict}车型图片筛选流水线 - 全流程自动化回归测试（{len(cars_to_test)}款车 × 2方向）")
    if args.quick:
        print("  (快速模式: 只跑A类方向判定，跳过B类+HTML+基线检查)")
    if args.strict:
        print("  (严格模式: 退出码需同时满足A类100% + B类100%)")
    print("=" * 90)

    md5s = {}
    md5_conflict = 0
    case_results = []
    car_summary = []

    # A类计数器（主指标，必须100%）
    step3_dir_pass = flip_logic_pass = direction_all_pass = 0
    # B类计数器（参考指标，do_baseline=False时始终=0）
    step1_pass = step2_pass = compliance_all_pass = 0
    total_cases = 0
    md5_1080p = 0

    for car in cars_to_test:
        brand, model = car["brand"], car["model"]
        name = f"{brand}/{model}"
        img_path = ROOT / "public" / "brands" / brand / f"{model}.jpg"

        if not img_path.exists():
            print(f"\n  ⚠️ 跳过 {name} - 图片不存在")
            car_summary.append({
                "brand": brand, "model": model, "name": name,
                "img_exists": False, "orig": None, "flip": None,
                "both_pass": False, "md5_unique": False,
            })
            continue

        # 基线检查：quick模式跳过
        if do_baseline:
            md5 = file_md5(img_path)
            if md5 in md5s:
                md5_conflict += 1
                md5_unique = False
                print(f"  ⚠️ MD5冲突 {name} = {md5s[md5]}")
            else:
                md5s[md5] = name
                md5_unique = True
            with Image.open(img_path) as im:
                w, h = im.size
            is_1080p = (w >= 1920 and h >= 1080) or (h >= 1920 and w >= 1080)
            if is_1080p:
                md5_1080p += 1
        else:
            md5_unique = True  # quick默认信任
            with Image.open(img_path) as im:
                w, h = im.size
            is_1080p = False

        orig_case = run_one_case(img_path, "left", quick=args.quick)
        flip_arr = np.array(Image.open(img_path).convert("RGB"))[:, ::-1, :].copy()
        flip_case = run_one_case(img_path, "right", arr_override=flip_arr, quick=args.quick)

        # 计数
        for case in (orig_case, flip_case):
            total_cases += 1
            # A类
            if case["dir_match"]: step3_dir_pass += 1
            if case["flip_logic_correct"]: flip_logic_pass += 1
            if case["direction_pass"]: direction_all_pass += 1
            # B类
            if do_baseline:
                if case["step1_white"]["pass"]: step1_pass += 1
                if case["step2_complete"]["pass"]: step2_pass += 1
                if case["compliance_pass"]: compliance_all_pass += 1

        both_pass = orig_case["direction_pass"] and flip_case["direction_pass"]
        if do_baseline:
            both_compliance = bool(orig_case["compliance_pass"] and flip_case["compliance_pass"])
        else:
            both_compliance = None
        orig_r = orig_case
        flip_r = flip_case

        # 打印单款车结果
        tags = []
        if do_baseline:
            if not md5_unique: tags.append("MD5重复")
            if not is_1080p: tags.append("<1080p")
            if both_compliance is False: tags.append("品牌图需预处理")
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        # A类方向判定必须通过；B类合规度是品牌图基线参考，用于标记但不影响主结论
        status = "✅" if both_pass and md5_unique else "❌"

        if do_baseline:
            s1p = "✓" if orig_r["step1_white"]["pass"] else "✗"
            s2p = "✓" + ("(填)" if orig_r["step2_padded"] else "") if orig_r["step2_complete"]["pass"] else "✗"
            f1p = "✓" if flip_r["step1_white"]["pass"] else "✗"
            f2p = "✓" + ("(填)" if flip_r["step2_padded"] else "") if flip_r["step2_complete"]["pass"] else "✗"
            line_prefix = f"[原图]白{s1p} 身{s2p} "
            line_suffix = f"[翻转]白{f1p} 身{f2p} "
        else:
            line_prefix = line_suffix = ""

        s3d = f"{orig_r['step3_direction']['direction']}"
        s3c = f"{orig_r['step3_direction']['confidence']:.0%}"
        s3w = orig_r["step3_direction"].get("wheel_source", "?")[:4]
        f3d = f"{flip_r['step3_direction']['direction']}"
        f3c = f"{flip_r['step3_direction']['confidence']:.0%}"
        f3w = flip_r["step3_direction"].get("wheel_source", "?")[:4]

        print(f"  {status} {name:<30} "
              f"{line_prefix}向{s3d}({s3c},{s3w}) "
              f"{line_suffix}向{f3d}({f3c},{f3w}){tag_str}")

        if args.verbose:
            # 详细模式：逐用例打印完整指标
            for label, case in [("原图", orig_case), ("翻转", flip_case)]:
                s1 = case["step1_white"]
                s2 = case["step2_complete"]
                s3 = case["step3_direction"]
                print(f"      └ {label}: 方向={s3['direction']} 置信={s3['confidence']:.0%} "
                      f"flip_needed={s3['flip_needed']} 轮源={s3.get('wheel_source','?')} "
                      f"L悬垂={s3.get('left_overhang','?')} R悬垂={s3.get('right_overhang','?')}")
                if do_baseline:
                    print(f"         白背景={'✓' if s1['pass'] else '✗'}({s1.get('white_ratio','?')}%,亮度{s1.get('brightness','?')}) "
                          f"车身={'✓' if s2['pass'] else '✗'}(宽{s2.get('width_ratio','?')},高{s2.get('height_ratio','?')}) "
                          f"{'[填充]' if case['step2_padded'] else ''}")

        car_summary.append({
            "brand": brand, "model": model, "name": name,
            "img_exists": True, "md5_unique": md5_unique,
            "is_1080p": is_1080p,
            "orig": orig_case, "flip": flip_case,
            "both_pass": both_pass,
            "both_compliance": both_compliance,
            "img_path": str(img_path),
            "w": w, "h": h, "size_kb": img_path.stat().st_size // 1024,
        })
        case_results.append(("orig", name, orig_case, img_path))
        case_results.append(("flip", name, flip_case, img_path))

    # ==================== 汇总 ====================
    cars_exist = [c for c in car_summary if c["img_exists"]]
    cars_dir_pass = sum(1 for c in cars_exist if c["both_pass"])
    cars_comp_pass = sum(1 for c in cars_exist if c.get("both_compliance") is True)
    n_cars = len(cars_to_test)

    print()
    print("=" * 90)
    print(f"  【A类 · 方向判定核心能力】总用例数: {total_cases} ({n_cars}款车 × 2方向) — 必须100%")
    print(f"    方向匹配:             {step3_dir_pass}/{total_cases} 通过 ({step3_dir_pass/total_cases*100:.0f}%)")
    print(f"    flip_needed逻辑正确:  {flip_logic_pass}/{total_cases} 通过 ({flip_logic_pass/total_cases*100:.0f}%)")
    print(f"    方向+flip联合通过:    {direction_all_pass}/{total_cases} 通过 ({direction_all_pass/total_cases*100:.0f}%)")
    print(f"    {n_cars}款车双用例全部通过: {cars_dir_pass}/{n_cars} ({cars_dir_pass/(n_cars if n_cars else 1)*100:.0f}%)")
    if do_baseline:
        print(f"    MD5唯一性:            {len(cars_exist)-md5_conflict}/{len(cars_exist)} 唯一 (冲突{md5_conflict}, 必须=0)")
        print(f"    1080p+分辨率:         {md5_1080p}/{len(cars_exist)}")
    print()
    if do_baseline:
        print(f"  【B类 · 图片合规度基线】参考指标（品牌图基线，非关键指标）")
        print(f"    纯白背景过滤通过:     {step1_pass}/{total_cases} ({step1_pass/total_cases*100:.0f}%)")
        print(f"    完整车身检测通过:     {step2_pass}/{total_cases} ({step2_pass/total_cases*100:.0f}%)")
        print(f"    合规度联合通过:       {compliance_all_pass}/{total_cases} ({compliance_all_pass/total_cases*100:.0f}%)")
        print(f"    {n_cars}款车双用例合规: {cars_comp_pass}/{n_cars} ({cars_comp_pass/(n_cars if n_cars else 1)*100:.0f}%)")
    else:
        print(f"  【B类 · 图片合规度基线】已跳过（快速模式）")
    print("=" * 90)

    # 只在A类方向判定失败时输出失败详情
    a_fail = direction_all_pass < total_cases
    if not args.quick:
        a_fail = a_fail or md5_conflict > 0
    if a_fail:
        print("\n  ❌ A类方向判定失败用例:")
        for case_type, name, case, path in case_results:
            if not case["direction_pass"]:
                failures = []
                if not case["dir_match"]: failures.append(f"方向匹配失败({case['step3_direction']['direction']})")
                if not case["flip_logic_correct"]: failures.append(f"flip_needed逻辑错误")
                print(f"    [{case_type:4s}] {name}: {' | '.join(failures)}")
        if md5_conflict > 0:
            print(f"    MD5冲突: {md5_conflict} 组")
    else:
        print("\n  ✅ A类方向判定核心能力 100% 通过！")
        if do_baseline:
            print("     (B类图片合规度反映品牌图基线质量，供参考；真正的候选图在流水线步骤1+2中会被过滤)")

    # ==================== 导出JSON（可选） ====================
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_report = {
            "args": vars(args),
            "summary": {
                "total_cases": total_cases, "cars": n_cars,
                "a": {
                    "dir_match": step3_dir_pass,
                    "flip_logic": flip_logic_pass,
                    "direction_all": direction_all_pass,
                    "cars_pass": cars_dir_pass,
                },
            },
        }
        if do_baseline:
            json_report["summary"]["md5_conflict"] = md5_conflict
            json_report["summary"]["resolution_1080p"] = md5_1080p
            json_report["summary"]["b"] = {
                "step1": step1_pass, "step2": step2_pass,
                "compliance_all": compliance_all_pass, "cars_comp": cars_comp_pass,
            }
        # cars: 精简版（去掉arr_for_preview等大图字段）
        cars_light = []
        for c in car_summary:
            orig_lite = {k: v for k, v in c["orig"].items() if k != "arr_for_preview"} if c["orig"] else None
            flip_lite = {k: v for k, v in c["flip"].items() if k != "arr_for_preview"} if c["flip"] else None
            cars_light.append({
                "brand": c["brand"], "model": c["model"], "name": c["name"],
                "img_exists": c["img_exists"], "both_pass": c.get("both_pass"),
                "both_compliance": c.get("both_compliance"),
                "md5_unique": c.get("md5_unique"), "is_1080p": c.get("is_1080p"),
                "w": c.get("w"), "h": c.get("h"), "size_kb": c.get("size_kb"),
                "orig": orig_lite, "flip": flip_lite,
            })
        json_report["cars"] = cars_light
        json_path.write_text(json.dumps(json_report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ JSON报告已导出: {json_path}")

    # ==================== 生成HTML报告（可选，quick/no-html自动跳过） ====================
    if generate_html:
        print("\n  正在生成HTML报告...")
        html_parts = []
        title_suffix = f"（{len(cars_to_test)}款车 × 2方向 = {total_cases}用例）"
        if args.quick:
            title_suffix += " · [快速模式]"
        if args.strict:
            title_suffix += " · [严格模式]"
        html_parts.append(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>车型图片筛选流水线 - 全流程自动化回归报告{title_suffix}</title>
<style>
body{{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}}
h1{{text-align:center;color:#2ecc71;margin-bottom:4px}}
.sub{{text-align:center;color:#888;margin-bottom:20px;font-size:13px}}
.summary-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:24px}}
.summary-card{{background:#16213e;border-radius:10px;padding:14px;text-align:center;border:1px solid #2a2a4a}}
.summary-card .num{{font-size:28px;font-weight:bold}}
.summary-card .lbl{{font-size:12px;color:#888;margin-top:4px}}
.pass{{color:#2ecc71}} .fail{{color:#e74c3c}} .warn{{color:#f39c12}}
.card{{background:#16213e;border:2px solid #2a2a4a;border-radius:12px;padding:16px;margin-bottom:18px}}
.card-pass{{border-color:#2ecc71}}
.card-fail{{border-color:#e74c3c}}
.card-title{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}}
.card-title h3{{margin:0;color:#3498db}}
.pair{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.case-box{{background:#0a0f1e;border:1px solid #2a2a4a;border-radius:8px;padding:12px}}
.case-pass{{border-color:#2ecc71}}
.case-fail{{border-color:#e74c3c}}
.case-head{{font-weight:bold;margin-bottom:8px;font-size:14px}}
.img-wrap{{background:#111;border-radius:6px;overflow:hidden;margin-bottom:10px;text-align:center}}
.img-wrap img{{max-width:100%;max-height:220px;object-fit:contain;display:block;margin:0 auto;background:#fff}}
.metrics{{font-size:12px;line-height:1.8}}
.metrics .m-item{{display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px dashed #2a2a4a}}
.metrics .m-item:last-child{{border-bottom:none}}
.tag-pill{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;margin:0 2px}}
.tag-pill.pass{{background:#0a3a0a;color:#2ecc71}}
.tag-pill.fail{{background:#3a0a0a;color:#e74c3c}}
.tag-pill.warn{{background:#3a2a0a;color:#f39c12}}
table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:12px}}
th,td{{padding:6px 8px;text-align:left;border-bottom:1px solid #2a2a4a}}
th{{background:#1a1a2e;color:#3498db}}
.kpi-row{{font-size:12px;color:#aaa;margin-top:8px}}
</style></head><body>
<h1>🚗 EVOLUTION AI DESIGN - 车型图片筛选流水线</h1>
<div class="sub">全流程自动化回归测试 | {n_cars}款车 × 2方向(原图/翻转) = {total_cases}用例 | v3全自动算法</div>
""")

        # 汇总卡片
        pct = lambda a, b: f"{a/b*100:.0f}%" if b else "N/A"
        extra_a_cards = ""
        if do_baseline:
            md5_cls = "pass" if md5_conflict == 0 else "fail"
            res_cls = "pass" if md5_1080p == len(cars_exist) else "warn"
            extra_a_cards = (
                f'  <div class="summary-card"><div class="num {md5_cls}">{len(cars_exist)-md5_conflict}/{len(cars_exist)}</div><div class="lbl">MD5唯一（冲突{md5_conflict}）</div></div>\n'
                f'  <div class="summary-card"><div class="num {res_cls}">{md5_1080p}/{len(cars_exist)}</div><div class="lbl">1080p+分辨率</div></div>\n'
            )
        cls_1 = "pass" if step3_dir_pass == total_cases else "fail"
        cls_2 = "pass" if flip_logic_pass == total_cases else "fail"
        cls_3 = "pass" if direction_all_pass == total_cases else "fail"
        cls_4 = "pass" if cars_dir_pass == n_cars else "fail"
        html_parts.append(f"""
<h2 style="color:#2ecc71;margin-top:0">A类 · 方向判定核心能力（必须100%）</h2>
<div class="summary-grid">
  <div class="summary-card"><div class="num {cls_1}">{step3_dir_pass}/{total_cases}</div><div class="lbl">方向判定匹配 · {pct(step3_dir_pass,total_cases)}</div></div>
  <div class="summary-card"><div class="num {cls_2}">{flip_logic_pass}/{total_cases}</div><div class="lbl">flip_needed逻辑正确 · {pct(flip_logic_pass,total_cases)}</div></div>
  <div class="summary-card"><div class="num {cls_3}">{direction_all_pass}/{total_cases}</div><div class="lbl">方向联合通过 · {pct(direction_all_pass,total_cases)}</div></div>
  <div class="summary-card"><div class="num {cls_4}">{cars_dir_pass}/{n_cars}</div><div class="lbl">{n_cars}款车双用例全部通过</div></div>
{extra_a_cards}</div>
""")
        if do_baseline:
            html_parts.append(f"""
<h2 style="color:#f39c12;margin-top:20px">B类 · 图片合规度基线（参考指标）</h2>
<div class="summary-grid">
  <div class="summary-card"><div class="num warn">{step1_pass}/{total_cases}</div><div class="lbl">纯白背景过滤 · {pct(step1_pass,total_cases)}</div></div>
  <div class="summary-card"><div class="num warn">{step2_pass}/{total_cases}</div><div class="lbl">完整车身检测 · {pct(step2_pass,total_cases)}</div></div>
  <div class="summary-card"><div class="num warn">{compliance_all_pass}/{total_cases}</div><div class="lbl">合规度联合 · {pct(compliance_all_pass,total_cases)}</div></div>
  <div class="summary-card"><div class="num warn">{cars_comp_pass}/{n_cars}</div><div class="lbl">{n_cars}款车双用例合规</div></div>
</div>
""")

        # 每张车卡片
        for i, c in enumerate(car_summary):
            if not c["img_exists"]:
                html_parts.append(f'<div class="card card-fail"><div class="card-title"><h3>#{i+1} {c["name"]}</h3><span class="fail">❌ 图片不存在</span></div></div>\n')
                continue

            md5_unique = c.get("md5_unique", True)
            is_1080p = c.get("is_1080p", True)
            both_compliance = c.get("both_compliance", None)
            card_cls = "card-pass" if c["both_pass"] and md5_unique else "card-fail"
            status_text = "✅ A类方向判定通过" if c["both_pass"] and md5_unique else "❌ A类存在失败"
            extra_tags = ""
            if not md5_unique: extra_tags += '<span class="tag-pill fail">MD5重复</span>'
            if not is_1080p: extra_tags += '<span class="tag-pill warn">低于1080p</span>'
            if both_compliance is False: extra_tags += '<span class="tag-pill warn">合规待处理</span>'

            html_parts.append(f'<div class="card {card_cls}">')
            html_parts.append(f'  <div class="card-title"><h3>#{i+1} {c["name"]} ({c["w"]}×{c["h"]} · {c["size_kb"]}KB)</h3><div>{status_text} {extra_tags}</div></div>\n')
            html_parts.append(f'  <div class="pair">')

            for case_type, case in [("原图(期望车头向左)", c["orig"]), ("翻转图(期望车头向右)", c["flip"])]:
                case_cls = "case-pass" if case["direction_pass"] else "case-fail"
                case_status = "✅ 方向判定通过" if case["direction_pass"] else "❌ 方向判定失败"
                comp_pass = case["compliance_pass"]
                comp_tag = '<span class="tag-pill warn">合规待处理</span>' if comp_pass is False else ""
                s1 = case["step1_white"]
                s2 = case["step2_complete"]
                s3 = case["step3_direction"]
                pad_tag = '<span class="tag-pill warn">白边填充</span>' if case["step2_padded"] else ""
                s1_pass_cls = "pass" if s1["pass"] else "fail"
                s2_pass_cls = "pass" if s2["pass"] else "fail"
                s3_match_cls = "pass" if case["dir_match"] else "fail"
                flip_cls = "pass" if case["flip_logic_correct"] else "fail"
                conf_cls = "pass" if s3["confidence"] >= DIRECTION_CONFIG["min_confidence"] else "warn"
                if args.no_inline_img:
                    if case_type.startswith("原图"):
                        img_data = f"/brands/{c['brand']}/{c['model']}.jpg"
                    else:
                        img_data = f"/brands/{c['brand']}/{c['model']}.jpg#flipped"
                else:
                    img_data = img_to_dataurl(case["arr_for_preview"])

                # quick模式下跳过的项，显示SKIP
                s1_disp = f"白{s1['white_ratio']}% · 亮度{s1['brightness']:.0f}" if do_baseline else "SKIP(quick)"
                s2_disp = f"宽占{s2.get('width_ratio',0)*100:.0f}% · 高占{s2.get('height_ratio',0)*100:.0f}%" if do_baseline else "SKIP(quick)"
                html_parts.append(f"""    <div class="case-box {case_cls}">
      <div class="case-head">{case_type} · {case_status} {comp_tag}</div>
      <div class="img-wrap"><img src="{img_data}" alt="{case_type}"></div>
      <div class="metrics">
        <div class="m-item"><span>① 纯白背景过滤 <span class="tag-pill {s1_pass_cls}">{'✓' if s1['pass'] else ('—' if s1['pass'] is None else '✗')}</span></span><span>{s1_disp}</span></div>
        <div class="m-item"><span>② 完整车身检测 <span class="tag-pill {s2_pass_cls}">{'✓' if s2['pass'] else ('—' if s2['pass'] is None else '✗')}</span> {pad_tag}</span><span>{s2_disp}</span></div>
        <div class="m-item"><span>③ 方向判定 <span class="tag-pill {s3_match_cls}">{'匹配' if case['dir_match'] else '不匹配'}</span></span><span>{s3['direction']} (置信度 <span class="{conf_cls}">{s3['confidence']:.0%}</span>)</span></div>
        <div class="m-item"><span>③ 轮源/悬垂</span><span>{s3.get('wheel_source','?')} · L{s3.get('left_overhang',0)} R{s3.get('right_overhang',0)}</span></div>
        <div class="m-item"><span>③ flip_needed <span class="tag-pill {flip_cls}">{'✓' if case['flip_logic_correct'] else '✗'}</span></span><span>{s3['flip_needed']}</span></div>
      </div>
    </div>\n""")

            html_parts.append(f'  </div>')  # pair end
            if not c["both_pass"]:
                fails = []
                for label, case in [("原图", c["orig"]), ("翻转", c["flip"])]:
                    s1_p = case["step1_white"]["pass"]
                    s2_p = case["step2_complete"]["pass"]
                    s1_fail = s1_p is False
                    s2_fail = s2_p is False
                    if not case["direction_pass"] or s1_fail or s2_fail:
                        parts = []
                        if s1_fail: parts.append(f"背景:{','.join(case['step1_white']['reasons'])}")
                        if s2_fail: parts.append(f"车身:{','.join(case['step2_complete'].get('reasons',['?']))}")
                        if not case["dir_match"]: parts.append(f"方向:{case['step3_direction']['direction']}")
                        if not case["flip_logic_correct"]: parts.append("flip逻辑错误")
                        if parts:
                            fails.append(f"[{label}] {' | '.join(parts)}")
                if fails:
                    html_parts.append(f'  <div class="kpi-row fail">失败原因: {"<br>".join(fails)}</div>\n')
            html_parts.append(f'</div>\n')  # card end

        # 底部总览表
        html_parts.append("""<div class="card"><div class="card-title"><h3>📊 总览表</h3></div>
<table>
<tr><th>#</th><th>车型</th>"""
                          + (f"<th>分辨率</th><th>MD5</th>" if do_baseline else "")
                          + (f"<th>1白(原/翻)</th><th>2身(原/翻)</th>" if do_baseline else "")
                          + f"""<th>3向(原/翻)</th><th>置信度</th><th>结果</th></tr>
""")
        for i, c in enumerate(car_summary):
            if not c["img_exists"]:
                colspan = 6 if do_baseline else 4
                html_parts.append(f"<tr><td>{i+1}</td><td>{c['name']}</td><td colspan={colspan} class='fail'>图片缺失</td></tr>")
                continue
            o_s1 = "✓" if c["orig"]["step1_white"]["pass"] else ("—" if c["orig"]["step1_white"]["pass"] is None else "✗")
            f_s1 = "✓" if c["flip"]["step1_white"]["pass"] else ("—" if c["flip"]["step1_white"]["pass"] is None else "✗")
            o_s2 = "✓" if c["orig"]["step2_complete"]["pass"] else ("—" if c["orig"]["step2_complete"]["pass"] is None else "✗")
            f_s2 = "✓" if c["flip"]["step2_complete"]["pass"] else ("—" if c["flip"]["step2_complete"]["pass"] is None else "✗")
            o_s3 = f"{c['orig']['step3_direction']['direction']}" if c["orig"]["dir_match"] else f"<span class='fail'>{c['orig']['step3_direction']['direction']}</span>"
            f_s3 = f"{c['flip']['step3_direction']['direction']}" if c["flip"]["dir_match"] else f"<span class='fail'>{c['flip']['step3_direction']['direction']}</span>"
            o_conf = f"{c['orig']['step3_direction']['confidence']:.0%}"
            f_conf = f"{c['flip']['step3_direction']['confidence']:.0%}"
            res = "✅" if c["both_pass"] and c.get("md5_unique", True) else "❌"
            html_parts.append(f"<tr><td>{i+1}</td><td>{c['name']}</td>")
            if do_baseline:
                md5_tag = "✓" if c.get("md5_unique", True) else '<span class="fail">✗重</span>'
                res_tag = f"{c['w']}×{c['h']}"
                html_parts.append(f"<td>{res_tag}</td><td>{md5_tag}</td>")
                html_parts.append(f"<td>{o_s1}/{f_s1}</td><td>{o_s2}/{f_s2}</td>")
            html_parts.append(f"<td>{o_s3}/{f_s3}</td>")
            html_parts.append(f"<td>{o_conf}/{f_conf}</td><td>{res}</td></tr>\n")
        html_parts.append("</table></div>")
        html_parts.append("</body></html>")

        if args.html_out:
            out = Path(args.html_out)
        else:
            out = ROOT / "public" / "_test_pipeline_e2e_report.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(html_parts), encoding="utf-8")
        try:
            rel = out.resolve().relative_to((ROOT / "public").resolve())
            url = f"http://localhost:5173/{rel.as_posix()}"
            print(f"  ✅ HTML报告已生成: {url}")
        except Exception:
            print(f"  ✅ HTML报告已生成: {out}")
        print(f"     文件大小: {out.stat().st_size//1024}KB")
    else:
        print(f"\n  📌 跳过HTML报告（{'快速模式' if args.quick else '用户指定--no-html'}）")

    # ==================== 统一退出码 ====================
    a_ok = (direction_all_pass == total_cases)
    md5_ok = True if args.quick else (md5_conflict == 0)
    ok = a_ok and md5_ok
    if args.strict and do_baseline:
        b_ok = (compliance_all_pass == total_cases)
        ok = ok and b_ok
        if not b_ok:
            print(f"\n  [严格模式] ❌ B类合规度未达100%：{compliance_all_pass}/{total_cases}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
