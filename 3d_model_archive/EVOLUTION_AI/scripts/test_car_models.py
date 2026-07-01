"""
EVOLUTION AI - 25种车型参数对比测试报告
生成完整的参数对比报告，验证国标合规性和参数合理性
"""

import json
import os
from datetime import datetime

# 国标GB 1589-2016 乘用车限值
GB = {"maxL": 5.3, "maxW": 2.55, "maxH": 4.0, "minGC": 0.13}

# 25种车型真实参数（与前端MODELS同步）
MODELS = {
    "sedan_c": {
        "name": "C级轿车", "ico": "🚗", "brand": "蔚来ET7 / 奔驰E级 / 宝马5系",
        "benchmark": "蔚来ET7 L=5101 WB=3060",
        "L": 5.10, "W": 1.99, "H": 1.51, "WB": 3.06,
        "FO": 0.85, "RO": 1.19, "GC": 0.14, "WR": 0.33,
        "TW": 1.66, "AA": 26, "CA": 40, "WL": 0.68, "WBulge": 0.03
    },
    "sedan_d": {
        "name": "D级轿车", "ico": "🚘", "brand": "奔驰S级 / 宝马7系 / 奥迪A8L",
        "benchmark": "奔驰S级 L=5290 WB=3216",
        "L": 5.29, "W": 1.92, "H": 1.50, "WB": 3.22,
        "FO": 0.87, "RO": 1.20, "GC": 0.13, "WR": 0.35,
        "TW": 1.62, "AA": 24, "CA": 38, "WL": 0.70, "WBulge": 0.04
    },
    "compact": {
        "name": "紧凑轿车", "ico": "🚙", "brand": "奥迪A3 / 宝马i3 NK / 奔驰C级EV",
        "benchmark": "奥迪A3L L=4606 WB=2730",
        "L": 4.61, "W": 1.81, "H": 1.43, "WB": 2.73,
        "FO": 0.79, "RO": 1.09, "GC": 0.14, "WR": 0.31,
        "TW": 1.54, "AA": 28, "CA": 42, "WL": 0.65, "WBulge": 0.02
    },
    "wagon": {
        "name": "旅行车", "ico": "🏕️", "brand": "蔚来ET5T / 奥迪A4 Avant / 奔驰C级旅行",
        "benchmark": "蔚来ET5T L=4790 WB=2888",
        "L": 4.79, "W": 1.96, "H": 1.50, "WB": 2.89,
        "FO": 0.80, "RO": 1.10, "GC": 0.14, "WR": 0.33,
        "TW": 1.64, "AA": 26, "CA": 55, "WL": 0.68, "WBulge": 0.02
    },
    "limo": {
        "name": "加长轿车", "ico": "🎩", "brand": "迈巴赫S级 / 奔驰S级 / 宝马7系长轴",
        "benchmark": "迈巴赫S级 L=5470 WB=3396",
        "L": 5.47, "W": 1.92, "H": 1.51, "WB": 3.40,
        "FO": 0.87, "RO": 1.20, "GC": 0.13, "WR": 0.35,
        "TW": 1.62, "AA": 22, "CA": 36, "WL": 0.70, "WBulge": 0.03
    },
    "suv_mid": {
        "name": "中型SUV", "ico": "🚜", "brand": "蔚来ES6 / 奔驰GLC EV / 宝马iX3 NK",
        "benchmark": "蔚来ES6 L=4854 WB=2915",
        "L": 4.85, "W": 2.00, "H": 1.70, "WB": 2.92,
        "FO": 0.81, "RO": 1.12, "GC": 0.20, "WR": 0.37,
        "TW": 1.66, "AA": 30, "CA": 45, "WL": 0.82, "WBulge": 0.02
    },
    "suv_full": {
        "name": "大型SUV", "ico": "🏔️", "brand": "宝马X5 / 奔驰GLE / 奥迪Q7",
        "benchmark": "宝马X5 L=5060 WB=3105",
        "L": 5.06, "W": 2.00, "H": 1.78, "WB": 3.11,
        "FO": 0.82, "RO": 1.13, "GC": 0.22, "WR": 0.40,
        "TW": 1.68, "AA": 32, "CA": 48, "WL": 0.90, "WBulge": 0.01
    },
    "suv_compact": {
        "name": "紧凑SUV", "ico": "🌿", "brand": "奥迪Q3 / 奔驰GLA / 宝马X1",
        "benchmark": "奥迪Q3 L=4498 WB=2680",
        "L": 4.50, "W": 1.85, "H": 1.61, "WB": 2.68,
        "FO": 0.77, "RO": 1.05, "GC": 0.19, "WR": 0.34,
        "TW": 1.56, "AA": 30, "CA": 46, "WL": 0.78, "WBulge": 0.02
    },
    "suv_coupe": {
        "name": "轿跑SUV", "ico": "🦅", "brand": "保时捷Macan EV / 宝马X4 / 奔驰GLC Coupe",
        "benchmark": "保时捷Macan EV L=4784 WB=2893",
        "L": 4.78, "W": 1.94, "H": 1.62, "WB": 2.89,
        "FO": 0.79, "RO": 1.10, "GC": 0.19, "WR": 0.37,
        "TW": 1.62, "AA": 26, "CA": 38, "WL": 0.74, "WBulge": 0.04
    },
    "micro_suv": {
        "name": "小型SUV", "ico": "🌱", "brand": "奥迪Q2 / 宝马X2 / 奔驰GLB",
        "benchmark": "奥迪Q2 L=4229 WB=2628",
        "L": 4.23, "W": 1.79, "H": 1.55, "WB": 2.63,
        "FO": 0.67, "RO": 0.93, "GC": 0.18, "WR": 0.31,
        "TW": 1.50, "AA": 32, "CA": 50, "WL": 0.74, "WBulge": 0.01
    },
    "crossover": {
        "name": "跨界车", "ico": "🛤️", "brand": "保时捷Macan / 奥迪Q3 Sportback / 宝马X2",
        "benchmark": "保时捷Macan EV L=4784 WB=2893",
        "L": 4.78, "W": 1.94, "H": 1.62, "WB": 2.89,
        "FO": 0.79, "RO": 1.10, "GC": 0.18, "WR": 0.33,
        "TW": 1.56, "AA": 30, "CA": 48, "WL": 0.76, "WBulge": 0.02
    },
    "coupe": {
        "name": "轿跑", "ico": "🏎️", "brand": "保时捷911 / 奔驰AMG GT / 宝马8系",
        "benchmark": "保时捷911 L=4519 WB=2450",
        "L": 4.52, "W": 1.85, "H": 1.30, "WB": 2.45,
        "FO": 0.92, "RO": 1.15, "GC": 0.12, "WR": 0.33,
        "TW": 1.56, "AA": 22, "CA": 35, "WL": 0.62, "WBulge": 0.05
    },
    "sports": {
        "name": "超跑", "ico": "🏁", "brand": "法拉利296 / 保时捷918 / 奔驰AMG ONE",
        "benchmark": "法拉利296 GTB L=4565 WB=2600",
        "L": 4.57, "W": 1.96, "H": 1.19, "WB": 2.60,
        "FO": 0.87, "RO": 1.10, "GC": 0.10, "WR": 0.34,
        "TW": 1.64, "AA": 20, "CA": 32, "WL": 0.55, "WBulge": 0.06
    },
    "roadster": {
        "name": "敞篷跑车", "ico": "🌊", "brand": "保时捷718 / 奔驰SL / 宝马Z4",
        "benchmark": "保时捷718 L=4379 WB=2475",
        "L": 4.38, "W": 1.80, "H": 1.27, "WB": 2.48,
        "FO": 0.85, "RO": 1.05, "GC": 0.11, "WR": 0.33,
        "TW": 1.52, "AA": 20, "CA": 30, "WL": 0.56, "WBulge": 0.05
    },
    "hatchback": {
        "name": "掀背车", "ico": "🚐", "brand": "奥迪A3 Sportback / 奔驰A级 / 宝马1系",
        "benchmark": "奥迪A3 SB L=4354 WB=2630",
        "L": 4.35, "W": 1.82, "H": 1.46, "WB": 2.63,
        "FO": 0.72, "RO": 1.00, "GC": 0.14, "WR": 0.31,
        "TW": 1.54, "AA": 28, "CA": 50, "WL": 0.66, "WBulge": 0.02
    },
    "mpv": {
        "name": "MPV", "ico": "🚌", "brand": "奔驰V级 / 蔚来EL8 / 奥迪Q8",
        "benchmark": "奔驰V级 L=5140 WB=3200",
        "L": 5.14, "W": 1.93, "H": 1.88, "WB": 3.20,
        "FO": 0.82, "RO": 1.12, "GC": 0.16, "WR": 0.34,
        "TW": 1.62, "AA": 24, "CA": 52, "WL": 0.85, "WBulge": 0.01
    },
    "van": {
        "name": "轻客", "ico": "🚚", "brand": "奔驰Sprinter / 奔驰Vito / 奥迪e-tron GT",
        "benchmark": "奔驰Sprinter L=5932 WB=3665",
        "L": 5.93, "W": 1.99, "H": 1.98, "WB": 3.67,
        "FO": 0.95, "RO": 1.31, "GC": 0.18, "WR": 0.35,
        "TW": 1.72, "AA": 22, "CA": 58, "WL": 0.95, "WBulge": 0.01
    },
    "pickup": {
        "name": "皮卡", "ico": "🛻", "brand": "奔驰X级 / 奥迪RS Q8 / 保时捷Cayenne",
        "benchmark": "奔驰X级 L=5340 WB=3150",
        "L": 5.34, "W": 1.92, "H": 1.82, "WB": 3.15,
        "FO": 0.92, "RO": 1.27, "GC": 0.22, "WR": 0.39,
        "TW": 1.68, "AA": 34, "CA": 50, "WL": 0.92, "WBulge": 0.01
    },
    "ev_sedan": {
        "name": "电动轿车", "ico": "⚡", "brand": "蔚来ET5 / 奥迪e-tron GT / 保时捷Taycan",
        "benchmark": "蔚来ET5 L=4790 WB=2888",
        "L": 4.79, "W": 1.96, "H": 1.50, "WB": 2.89,
        "FO": 0.80, "RO": 1.10, "GC": 0.14, "WR": 0.34,
        "TW": 1.64, "AA": 24, "CA": 36, "WL": 0.66, "WBulge": 0.04
    },
    "ev_suv": {
        "name": "电动SUV", "ico": "🔋", "brand": "蔚来ES6 / 奔驰EQE SUV / 宝马iX3",
        "benchmark": "蔚来ES6 L=4854 WB=2915",
        "L": 4.85, "W": 2.00, "H": 1.70, "WB": 2.92,
        "FO": 0.81, "RO": 1.12, "GC": 0.18, "WR": 0.36,
        "TW": 1.66, "AA": 28, "CA": 44, "WL": 0.80, "WBulge": 0.02
    },
    "ev_compact": {
        "name": "电动紧凑", "ico": "💡", "brand": "奥迪Q4 e-tron / 奔驰EQA / 宝马iX1",
        "benchmark": "奥迪Q4 e-tron L=4588 WB=2765",
        "L": 4.59, "W": 1.87, "H": 1.63, "WB": 2.77,
        "FO": 0.76, "RO": 1.06, "GC": 0.15, "WR": 0.31,
        "TW": 1.56, "AA": 28, "CA": 44, "WL": 0.66, "WBulge": 0.03
    },
    "ev_hatch": {
        "name": "电动两厢", "ico": "🔌", "brand": "保时捷Macan EV / 奥迪Q4 e-tron / 奔驰EQA",
        "benchmark": "保时捷Macan EV L=4784 WB=2893",
        "L": 4.78, "W": 1.94, "H": 1.62, "WB": 2.89,
        "FO": 0.79, "RO": 1.10, "GC": 0.16, "WR": 0.30,
        "TW": 1.52, "AA": 30, "CA": 50, "WL": 0.70, "WBulge": 0.02
    },
    "ev_pickup": {
        "name": "电动皮卡", "ico": "⚡", "brand": "奥迪Q8 e-tron / 奔驰EQG / 保时捷Cayenne E-Hybrid",
        "benchmark": "奥迪Q8 e-tron L=4915 WB=2928",
        "L": 4.92, "W": 1.98, "H": 1.68, "WB": 2.93,
        "FO": 0.84, "RO": 1.15, "GC": 0.22, "WR": 0.40,
        "TW": 1.72, "AA": 32, "CA": 48, "WL": 0.94, "WBulge": 0.01
    },
    "minicar": {
        "name": "微型车", "ico": "🛺", "brand": "MINI Cooper / smart fortwo / 奥迪AI:ME",
        "benchmark": "MINI Cooper L=3858 WB=2520",
        "L": 3.86, "W": 1.76, "H": 1.46, "WB": 2.52,
        "FO": 0.56, "RO": 0.78, "GC": 0.15, "WR": 0.28,
        "TW": 1.48, "AA": 32, "CA": 55, "WL": 0.72, "WBulge": 0.01
    },
    "kei_car": {
        "name": "K-Car", "ico": "🇯🇵", "brand": "smart fortwo / MINI / 奥迪AI:ME",
        "benchmark": "smart fortwo L=2695 WB=1873",
        "L": 2.70, "W": 1.66, "H": 1.56, "WB": 1.87,
        "FO": 0.35, "RO": 0.48, "GC": 0.15, "WR": 0.27,
        "TW": 1.40, "AA": 34, "CA": 58, "WL": 0.78, "WBulge": 0.01
    }
}

# 参数中文名映射
PARAM_NAMES = {
    "L": "车长(m)", "W": "车宽(m)", "H": "车高(m)", "WB": "轴距(m)",
    "FO": "前悬(m)", "RO": "后悬(m)", "GC": "离地间隙(m)", "WR": "轮径(m)",
    "TW": "轮距(m)", "AA": "A柱角(°)", "CA": "C柱角(°)",
    "WL": "腰线高(m)", "WBulge": "轮拱凸出(m)"
}

# 参数合理范围
PARAM_RANGES = {
    "L": (2.5, 6.0), "W": (1.4, 2.2), "H": (1.0, 2.8), "WB": (1.8, 4.0),
    "FO": (0.3, 1.2), "RO": (0.3, 1.5), "GC": (0.08, 0.30), "WR": (0.24, 0.45),
    "TW": (1.2, 1.8), "AA": (15, 40), "CA": (25, 65),
    "WL": (0.4, 1.0), "WBulge": (0.0, 0.10)
}


def check_gb1589(m):
    """检查国标GB 1589-2016合规性"""
    issues = []
    if m["L"] > GB["maxL"]:
        issues.append(f"车长{m['L']:.2f}m > 限值{GB['maxL']}m")
    if m["W"] > GB["maxW"]:
        issues.append(f"车宽{m['W']:.2f}m > 限值{GB['maxW']}m")
    if m["H"] > GB["maxH"]:
        issues.append(f"车高{m['H']:.2f}m > 限值{GB['maxH']}m")
    if m["GC"] < GB["minGC"]:
        issues.append(f"离地间隙{m['GC']:.2f}m < 限值{GB['minGC']}m")
    return issues


def check_param_range(m):
    """检查参数是否在合理范围内"""
    issues = []
    for k, (lo, hi) in PARAM_RANGES.items():
        v = m.get(k, 0)
        if v < lo or v > hi:
            issues.append(f"{PARAM_NAMES[k]}={v} 超出范围[{lo},{hi}]")
    return issues


def check_geometry(m):
    """检查几何一致性"""
    issues = []
    # FO + WB + RO 应约等于 L
    total = m["FO"] + m["WB"] + m["RO"]
    diff = abs(total - m["L"])
    if diff > 0.15:
        issues.append(f"FO+WB+RO={total:.2f}m ≠ L={m['L']:.2f}m (差{diff:.2f}m)")

    # 轮心高度 = GC + WR
    wheel_center = m["GC"] + m["WR"]
    if wheel_center > m["WL"]:
        issues.append(f"轮心高{wheel_center:.2f}m > 腰线{m['WL']:.2f}m")

    # TW 应小于 W
    if m["TW"] >= m["W"]:
        issues.append(f"轮距{m['TW']:.2f}m >= 车宽{m['W']:.2f}m")

    # WR*2 应小于 H
    if m["WR"] * 2 > m["H"] * 0.6:
        issues.append(f"轮径{m['WR']*2:.2f}m > 车高60%={m['H']*0.6:.2f}m")

    return issues


def check_proportions(m):
    """检查比例合理性"""
    issues = []
    # 轴距/车长比（通常0.55-0.70）
    wb_ratio = m["WB"] / m["L"]
    if wb_ratio < 0.55:
        issues.append(f"轴距/车长比={wb_ratio:.2f} < 0.55（短轴距）")
    elif wb_ratio > 0.70:
        issues.append(f"轴距/车长比={wb_ratio:.2f} > 0.70（长轴距）")

    # 前/后悬比
    fo_ratio = m["FO"] / (m["FO"] + m["RO"])
    if fo_ratio < 0.35:
        issues.append(f"前悬占比={fo_ratio:.2f} < 0.35（后悬过长）")
    elif fo_ratio > 0.55:
        issues.append(f"前悬占比={fo_ratio:.2f} > 0.55（前悬过长）")

    # 高宽比（通常0.65-0.95）
    hw_ratio = m["H"] / m["W"]
    if hw_ratio < 0.60:
        issues.append(f"高宽比={hw_ratio:.2f} < 0.60（极低车身）")
    elif hw_ratio > 1.0:
        issues.append(f"高宽比={hw_ratio:.2f} > 1.00（箱式车身）")

    return issues


def generate_report():
    """生成完整参数对比报告"""
    report = []
    report.append("=" * 100)
    report.append("EVOLUTION AI - 25种车型参数对比测试报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"国标依据: GB 1589-2016 (乘用车 L≤{GB['maxL']}m W≤{GB['maxW']}m H≤{GB['maxH']}m GC≥{GB['minGC']}m)")
    report.append("=" * 100)

    # === 1. 参数总表 ===
    report.append("\n" + "─" * 100)
    report.append("一、25种车型参数总表")
    report.append("─" * 100)

    # 表头
    header = f"{'车型':<12} {'L(m)':>6} {'W(m)':>6} {'H(m)':>6} {'WB(m)':>6} {'FO(m)':>6} {'RO(m)':>6} {'GC(m)':>6} {'WR(m)':>6} {'TW(m)':>6} {'AA(°)':>6} {'CA(°)':>6} {'WL(m)':>6} {'WBulge':>6}"
    report.append(header)
    report.append("-" * len(header))

    for key in MODELS:
        m = MODELS[key]
        row = f"{m['name']:<12} {m['L']:>6.2f} {m['W']:>6.2f} {m['H']:>6.2f} {m['WB']:>6.2f} {m['FO']:>6.2f} {m['RO']:>6.2f} {m['GC']:>6.2f} {m['WR']:>6.2f} {m['TW']:>6.2f} {m['AA']:>6.0f} {m['CA']:>6.0f} {m['WL']:>6.2f} {m['WBulge']:>6.2f}"
        report.append(row)

    # === 2. 国标合规检查 ===
    report.append("\n" + "─" * 100)
    report.append("二、国标GB 1589-2016合规性检查")
    report.append("─" * 100)

    gb_pass = 0
    gb_fail = 0
    for key in MODELS:
        m = MODELS[key]
        issues = check_gb1589(m)
        if issues:
            gb_fail += 1
            report.append(f"  ❌ {m['name']}: {'; '.join(issues)}")
        else:
            gb_pass += 1
            report.append(f"  ✅ {m['name']}: 合规")

    report.append(f"\n  合规: {gb_pass}/25 | 违规: {gb_fail}/25")

    # === 3. 几何一致性检查 ===
    report.append("\n" + "─" * 100)
    report.append("三、几何一致性检查 (FO+WB+RO≈L)")
    report.append("─" * 100)

    for key in MODELS:
        m = MODELS[key]
        total = m["FO"] + m["WB"] + m["RO"]
        diff = total - m["L"]
        status = "✅" if abs(diff) < 0.15 else "⚠️"
        report.append(f"  {status} {m['name']}: FO+WB+RO={total:.2f}m, L={m['L']:.2f}m, 差值={diff:+.2f}m")

    # === 4. 比例合理性检查 ===
    report.append("\n" + "─" * 100)
    report.append("四、比例合理性检查")
    report.append("─" * 100)

    for key in MODELS:
        m = MODELS[key]
        issues = check_proportions(m)
        if issues:
            report.append(f"  ⚠️ {m['name']}: {'; '.join(issues)}")
        else:
            wb_ratio = m["WB"] / m["L"]
            hw_ratio = m["H"] / m["W"]
            report.append(f"  ✅ {m['name']}: 轴距/车长={wb_ratio:.2f}, 高宽比={hw_ratio:.2f}")

    # === 5. 参数范围检查 ===
    report.append("\n" + "─" * 100)
    report.append("五、参数范围检查")
    report.append("─" * 100)

    for key in MODELS:
        m = MODELS[key]
        issues = check_param_range(m)
        if issues:
            report.append(f"  ⚠️ {m['name']}: {'; '.join(issues)}")
        else:
            report.append(f"  ✅ {m['name']}: 所有参数在合理范围内")

    # === 6. 几何约束检查 ===
    report.append("\n" + "─" * 100)
    report.append("六、几何约束检查 (轮心<腰线, 轮距<车宽)")
    report.append("─" * 100)

    for key in MODELS:
        m = MODELS[key]
        issues = check_geometry(m)
        if issues:
            report.append(f"  ⚠️ {m['name']}: {'; '.join(issues)}")
        else:
            wc = m["GC"] + m["WR"]
            report.append(f"  ✅ {m['name']}: 轮心高={wc:.2f}m, 腰线={m['WL']:.2f}m, 轮距/车宽={m['TW']/m['W']:.2f}")

    # === 7. 尺寸排名 ===
    report.append("\n" + "─" * 100)
    report.append("七、尺寸排名")
    report.append("─" * 100)

    for param, name in [("L", "车长"), ("W", "车宽"), ("H", "车高"), ("WB", "轴距"), ("GC", "离地间隙")]:
        sorted_models = sorted(MODELS.items(), key=lambda x: x[1][param], reverse=True)
        report.append(f"\n  {name}排名 (大到小):")
        for i, (key, m) in enumerate(sorted_models):
            unit = "m" if param != "AA" and param != "CA" else "°"
            report.append(f"    {i+1:>2}. {m['name']:<10} {m[param]:.2f}{unit}")

    # === 8. 同类对比 ===
    report.append("\n" + "─" * 100)
    report.append("八、同类车型参数对比")
    report.append("─" * 100)

    categories = {
        "轿车": ["sedan_c", "sedan_d", "compact", "wagon", "limo"],
        "SUV": ["suv_mid", "suv_full", "suv_compact", "suv_coupe", "micro_suv", "crossover"],
        "跑车": ["coupe", "sports", "roadster", "hatchback"],
        "MPV/皮卡": ["mpv", "van", "pickup"],
        "电动": ["ev_sedan", "ev_suv", "ev_compact", "ev_hatch", "ev_pickup"],
        "微型": ["minicar", "kei_car"]
    }

    for cat_name, cat_keys in categories.items():
        report.append(f"\n  【{cat_name}】")
        cat_models = [(k, MODELS[k]) for k in cat_keys if k in MODELS]
        if not cat_models:
            continue

        # 计算平均值
        avg = {}
        for param in ["L", "W", "H", "WB", "GC"]:
            vals = [m[param] for _, m in cat_models]
            avg[param] = sum(vals) / len(vals)

        report.append(f"    平均: L={avg['L']:.2f}m W={avg['W']:.2f}m H={avg['H']:.2f}m WB={avg['WB']:.2f}m GC={avg['GC']:.2f}m")
        for key, m in cat_models:
            diff_l = m["L"] - avg["L"]
            report.append(f"    {m['name']:<10} L={m['L']:.2f}m({diff_l:+.2f}) W={m['W']:.2f}m H={m['H']:.2f}m WB={m['WB']:.2f}m")

    # === 9. 标杆数据验证 ===
    report.append("\n" + "─" * 100)
    report.append("九、标杆车型数据验证")
    report.append("─" * 100)

    # 真实市场数据（mm）
    real_data = {
        "sedan_c": {"name": "蔚来ET7", "L": 5101, "W": 1987, "H": 1509, "WB": 3060},
        "sedan_d": {"name": "奔驰S级", "L": 5290, "W": 1921, "H": 1503, "WB": 3216},
        "compact": {"name": "奥迪A3L", "L": 4606, "W": 1814, "H": 1432, "WB": 2730},
        "wagon": {"name": "蔚来ET5T", "L": 4790, "W": 1960, "H": 1499, "WB": 2888},
        "limo": {"name": "迈巴赫S级", "L": 5470, "W": 1921, "H": 1510, "WB": 3396},
        "suv_mid": {"name": "蔚来ES6", "L": 4854, "W": 1995, "H": 1703, "WB": 2915},
        "suv_full": {"name": "宝马X5", "L": 5060, "W": 2004, "H": 1779, "WB": 3105},
        "suv_compact": {"name": "奥迪Q3", "L": 4498, "W": 1848, "H": 1614, "WB": 2680},
        "suv_coupe": {"name": "Macan EV", "L": 4784, "W": 1938, "H": 1622, "WB": 2893},
        "micro_suv": {"name": "奥迪Q2", "L": 4229, "W": 1785, "H": 1548, "WB": 2628},
        "coupe": {"name": "保时捷911", "L": 4519, "W": 1852, "H": 1298, "WB": 2450},
        "sports": {"name": "法拉利296", "L": 4565, "W": 1958, "H": 1186, "WB": 2600},
        "roadster": {"name": "保时捷718", "L": 4379, "W": 1801, "H": 1272, "WB": 2475},
        "hatchback": {"name": "奥迪A3 SB", "L": 4354, "W": 1815, "H": 1458, "WB": 2630},
        "mpv": {"name": "奔驰V级", "L": 5140, "W": 1928, "H": 1880, "WB": 3200},
        "van": {"name": "Sprinter", "L": 5932, "W": 1993, "H": 1980, "WB": 3665},
        "pickup": {"name": "奔驰X级", "L": 5340, "W": 1920, "H": 1819, "WB": 3150},
        "ev_sedan": {"name": "蔚来ET5", "L": 4790, "W": 1960, "H": 1499, "WB": 2888},
        "ev_suv": {"name": "蔚来ES6", "L": 4854, "W": 1995, "H": 1703, "WB": 2915},
        "ev_compact": {"name": "Q4 e-tron", "L": 4588, "W": 1865, "H": 1626, "WB": 2765},
        "ev_hatch": {"name": "Macan EV", "L": 4784, "W": 1938, "H": 1622, "WB": 2893},
        "ev_pickup": {"name": "Q8 e-tron", "L": 4915, "W": 1976, "H": 1680, "WB": 2928},
        "minicar": {"name": "MINI Cooper", "L": 3858, "W": 1756, "H": 1460, "WB": 2520},
        "kei_car": {"name": "smart fortwo", "L": 2695, "W": 1663, "H": 1555, "WB": 1873},
    }

    max_err = 0
    for key in MODELS:
        m = MODELS[key]
        rd = real_data.get(key)
        if not rd:
            report.append(f"  ⚠️ {m['name']}: 无标杆数据")
            continue

        err_l = abs(m["L"] * 1000 - rd["L"])
        err_w = abs(m["W"] * 1000 - rd["W"])
        err_h = abs(m["H"] * 1000 - rd["H"])
        err_wb = abs(m["WB"] * 1000 - rd["WB"])
        max_err = max(max_err, err_l, err_w, err_h, err_wb)

        status = "✅" if max(err_l, err_w, err_h, err_wb) < 50 else "⚠️"
        report.append(f"  {status} {m['name']:<10} vs {rd['name']}: L差{err_l:.0f}mm W差{err_w:.0f}mm H差{err_h:.0f}mm WB差{err_wb:.0f}mm")

    # === 10. 总结 ===
    report.append("\n" + "─" * 100)
    report.append("十、测试总结")
    report.append("─" * 100)

    total_issues = 0
    for key in MODELS:
        m = MODELS[key]
        issues = check_gb1589(m) + check_param_range(m) + check_geometry(m) + check_proportions(m)
        total_issues += len(issues)

    report.append(f"\n  测试车型数: {len(MODELS)}")
    report.append(f"  国标合规率: {gb_pass}/{len(MODELS)} ({gb_pass/len(MODELS)*100:.0f}%)")
    report.append(f"  总问题数: {total_issues}")
    report.append(f"  最大标杆偏差: {max_err:.0f}mm")
    report.append(f"  参数总数: {len(MODELS)} × 13 = {len(MODELS) * 13}")

    if total_issues == 0 and gb_pass == len(MODELS):
        report.append("\n  🎉 所有测试通过！25种车型参数全部合规且合理。")
    else:
        report.append(f"\n  ⚠️ 发现 {total_issues} 个潜在问题，请检查上方详细报告。")

    report.append("\n" + "=" * 100)

    return "\n".join(report)


if __name__ == "__main__":
    report = generate_report()

    # 输出到控制台
    print(report)

    # 保存到文件
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "car_model_test_report.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已保存到: {output_path}")
