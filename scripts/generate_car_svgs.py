import os
import math

BRAND_COLORS = {
    "rolls-royce": "#4ade80",
    "bentley": "#3b82f6",
    "bugatti": "#f59e0b",
    "porsche": "#ef4444",
    "ferrari": "#dc2626",
}

CARS = [
    {"brand_key": "rolls-royce", "model_key": "phantom", "model_name": "Phantom", "params": {"overall_length": 5770, "overall_width": 2018, "overall_height": 1648, "wheel_base": 3552, "track_width": 1680, "ground_clearance": 150, "hood_length": 1300, "roof_height": 750, "wheel_diameter": 750, "windshield_angle": 28, "rear_window_angle": 22, "rear_slant_angle": 12, "front_overhang": 1050, "rear_overhang": 1168}},
    {"brand_key": "rolls-royce", "model_key": "ghost", "model_name": "Ghost", "params": {"overall_length": 5546, "overall_width": 1948, "overall_height": 1550, "wheel_base": 3295, "track_width": 1640, "ground_clearance": 145, "hood_length": 1200, "roof_height": 650, "wheel_diameter": 720, "windshield_angle": 30, "rear_window_angle": 24, "rear_slant_angle": 14, "front_overhang": 1020, "rear_overhang": 1231}},
    {"brand_key": "rolls-royce", "model_key": "cullinan", "model_name": "Cullinan", "params": {"overall_length": 5341, "overall_width": 2000, "overall_height": 1835, "wheel_base": 3295, "track_width": 1680, "ground_clearance": 215, "hood_length": 1200, "roof_height": 900, "wheel_diameter": 780, "windshield_angle": 26, "rear_window_angle": 20, "rear_slant_angle": 10, "front_overhang": 970, "rear_overhang": 1076}},
    {"brand_key": "rolls-royce", "model_key": "wraith", "model_name": "Wraith", "params": {"overall_length": 5285, "overall_width": 1947, "overall_height": 1507, "wheel_base": 3112, "track_width": 1630, "ground_clearance": 135, "hood_length": 1400, "roof_height": 550, "wheel_diameter": 710, "windshield_angle": 38, "rear_window_angle": 32, "rear_slant_angle": 35, "front_overhang": 1090, "rear_overhang": 1083}},
    {"brand_key": "bentley", "model_key": "continental-gt", "model_name": "Continental GT", "params": {"overall_length": 4850, "overall_width": 1954, "overall_height": 1405, "wheel_base": 2851, "track_width": 1650, "ground_clearance": 125, "hood_length": 1450, "roof_height": 480, "wheel_diameter": 730, "windshield_angle": 38, "rear_window_angle": 33, "rear_slant_angle": 38, "front_overhang": 1000, "rear_overhang": 999}},
    {"brand_key": "bentley", "model_key": "continental-gtc", "model_name": "Continental GTC", "params": {"overall_length": 4850, "overall_width": 1954, "overall_height": 1405, "wheel_base": 2851, "track_width": 1650, "ground_clearance": 125, "hood_length": 1450, "roof_height": 480, "wheel_diameter": 730, "windshield_angle": 38, "rear_window_angle": 33, "rear_slant_angle": 38, "front_overhang": 1000, "rear_overhang": 999}},
    {"brand_key": "bentley", "model_key": "flying-spur", "model_name": "Flying Spur", "params": {"overall_length": 5316, "overall_width": 1978, "overall_height": 1484, "wheel_base": 3194, "track_width": 1660, "ground_clearance": 140, "hood_length": 1300, "roof_height": 600, "wheel_diameter": 730, "windshield_angle": 32, "rear_window_angle": 26, "rear_slant_angle": 16, "front_overhang": 1060, "rear_overhang": 1062}},
    {"brand_key": "bentley", "model_key": "bentayga", "model_name": "Bentayga", "params": {"overall_length": 5125, "overall_width": 1998, "overall_height": 1742, "wheel_base": 2995, "track_width": 1680, "ground_clearance": 200, "hood_length": 1200, "roof_height": 850, "wheel_diameter": 760, "windshield_angle": 28, "rear_window_angle": 22, "rear_slant_angle": 12, "front_overhang": 1030, "rear_overhang": 1100}},
    {"brand_key": "bugatti", "model_key": "chiron", "model_name": "Chiron", "params": {"overall_length": 4544, "overall_width": 2038, "overall_height": 1212, "wheel_base": 2711, "track_width": 1720, "ground_clearance": 95, "hood_length": 1550, "roof_height": 320, "wheel_diameter": 740, "windshield_angle": 48, "rear_window_angle": 42, "rear_slant_angle": 52, "front_overhang": 920, "rear_overhang": 913}},
    {"brand_key": "bugatti", "model_key": "veyron", "model_name": "Veyron", "params": {"overall_length": 4462, "overall_width": 1998, "overall_height": 1159, "wheel_base": 2710, "track_width": 1710, "ground_clearance": 90, "hood_length": 1500, "roof_height": 300, "wheel_diameter": 720, "windshield_angle": 46, "rear_window_angle": 40, "rear_slant_angle": 50, "front_overhang": 900, "rear_overhang": 852}},
    {"brand_key": "bugatti", "model_key": "divo", "model_name": "Divo", "params": {"overall_length": 4579, "overall_width": 2038, "overall_height": 1212, "wheel_base": 2711, "track_width": 1730, "ground_clearance": 90, "hood_length": 1550, "roof_height": 310, "wheel_diameter": 740, "windshield_angle": 50, "rear_window_angle": 44, "rear_slant_angle": 55, "front_overhang": 930, "rear_overhang": 938}},
    {"brand_key": "porsche", "model_key": "911", "model_name": "911 Carrera", "params": {"overall_length": 4519, "overall_width": 1852, "overall_height": 1299, "wheel_base": 2450, "track_width": 1580, "ground_clearance": 105, "hood_length": 1100, "roof_height": 400, "wheel_diameter": 680, "windshield_angle": 42, "rear_window_angle": 35, "rear_slant_angle": 45, "front_overhang": 920, "rear_overhang": 1149}},
    {"brand_key": "porsche", "model_key": "taycan", "model_name": "Taycan", "params": {"overall_length": 4963, "overall_width": 1966, "overall_height": 1381, "wheel_base": 2900, "track_width": 1660, "ground_clearance": 125, "hood_length": 1200, "roof_height": 500, "wheel_diameter": 710, "windshield_angle": 38, "rear_window_angle": 32, "rear_slant_angle": 35, "front_overhang": 980, "rear_overhang": 1083}},
    {"brand_key": "porsche", "model_key": "panamera", "model_name": "Panamera", "params": {"overall_length": 5049, "overall_width": 1937, "overall_height": 1423, "wheel_base": 2950, "track_width": 1650, "ground_clearance": 130, "hood_length": 1300, "roof_height": 550, "wheel_diameter": 710, "windshield_angle": 35, "rear_window_angle": 28, "rear_slant_angle": 30, "front_overhang": 1020, "rear_overhang": 1079}},
    {"brand_key": "porsche", "model_key": "cayenne", "model_name": "Cayenne", "params": {"overall_length": 4926, "overall_width": 1983, "overall_height": 1673, "wheel_base": 2895, "track_width": 1680, "ground_clearance": 190, "hood_length": 1200, "roof_height": 780, "wheel_diameter": 760, "windshield_angle": 28, "rear_window_angle": 22, "rear_slant_angle": 15, "front_overhang": 950, "rear_overhang": 1081}},
    {"brand_key": "porsche", "model_key": "macan", "model_name": "Macan", "params": {"overall_length": 4686, "overall_width": 1923, "overall_height": 1624, "wheel_base": 2807, "track_width": 1650, "ground_clearance": 180, "hood_length": 1150, "roof_height": 720, "wheel_diameter": 730, "windshield_angle": 30, "rear_window_angle": 24, "rear_slant_angle": 18, "front_overhang": 900, "rear_overhang": 979}},
    {"brand_key": "ferrari", "model_key": "sf90", "model_name": "SF90 Stradale", "params": {"overall_length": 4710, "overall_width": 1972, "overall_height": 1186, "wheel_base": 2650, "track_width": 1700, "ground_clearance": 90, "hood_length": 1450, "roof_height": 300, "wheel_diameter": 730, "windshield_angle": 50, "rear_window_angle": 45, "rear_slant_angle": 55, "front_overhang": 980, "rear_overhang": 1080}},
    {"brand_key": "ferrari", "model_key": "f8-tributo", "model_name": "F8 Tributo", "params": {"overall_length": 4611, "overall_width": 1979, "overall_height": 1206, "wheel_base": 2650, "track_width": 1700, "ground_clearance": 95, "hood_length": 1400, "roof_height": 320, "wheel_diameter": 720, "windshield_angle": 48, "rear_window_angle": 42, "rear_slant_angle": 52, "front_overhang": 950, "rear_overhang": 1011}},
    {"brand_key": "ferrari", "model_key": "roma", "model_name": "Roma", "params": {"overall_length": 4656, "overall_width": 1974, "overall_height": 1301, "wheel_base": 2670, "track_width": 1680, "ground_clearance": 105, "hood_length": 1350, "roof_height": 420, "wheel_diameter": 710, "windshield_angle": 40, "rear_window_angle": 34, "rear_slant_angle": 40, "front_overhang": 970, "rear_overhang": 1016}},
]

BASE_PATH = r"d:\API\Evolution-Ai.Design\public\brands"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))

def adjust_brightness(hex_color, factor):
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hex(max(0, min(255, r * factor)), max(0, min(255, g * factor)), max(0, min(255, b * factor)))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def generate_car_svg(car):
    brand_color = BRAND_COLORS[car["brand_key"]]
    p = car["params"]
    
    sx = 0.14
    sy = 0.28
    
    L = p["overall_length"] * sx
    H = p["overall_height"] * sy
    
    cx = 400.0
    wy = 350.0
    wr = (p["wheel_diameter"] * sx) / 2.0
    
    w1x = cx - L * 0.30
    w2x = cx + L * 0.30
    
    xl = cx - L / 2.0
    xr = cx + L / 2.0
    
    ground_y = wy + wr
    bb_y = ground_y - (p["ground_clearance"] * sy)
    
    hl = p["hood_length"] * sx
    foh = p["front_overhang"] * sx
    roh = p["rear_overhang"] * sx
    rh = p["roof_height"] * sy
    
    rt_y = bb_y - rh
    
    hx_start = xl + foh
    fx_wall = hx_start + hl
    
    wa = math.radians(p["windshield_angle"])
    ws_dx = rh * math.tan(wa)
    
    ws_bot_x = fx_wall
    ws_top_x = ws_bot_x + ws_dx
    ws_top_y = rt_y
    
    rwa = math.radians(p["rear_window_angle"])
    rws_dx = rh * math.tan(rwa)
    
    rws_bot_x = xr - roh
    rws_top_x = rws_bot_x - rws_dx
    rws_top_y = rt_y
    
    rs_x1 = ws_top_x
    rs_x2 = rws_top_x
    
    if rs_x2 < rs_x1 + 30:
        gap = 30 - (rs_x2 - rs_x1)
        rs_x1 -= gap / 2
        rs_x2 += gap / 2
    
    rsa = math.radians(p["rear_slant_angle"])
    rdeck_h = rh * 0.4
    rdeck_y = rt_y + rdeck_h
    rs_dx = rdeck_h * math.tan(rsa)
    
    rdeck_x1 = rs_x2
    rdeck_x2 = rdeck_x1 + rs_dx
    rdeck_x2 = clamp(rdeck_x2, rs_x2 + 10, xr - 8)
    
    hh = rh * 0.22
    hl_y = bb_y - hh
    
    fb_h = H * 0.48
    fb_top_y = bb_y - fb_h
    
    rb_h = H * 0.48
    rb_top_y = bb_y - rb_h
    
    rdeck_final_y = bb_y - (H * 0.32)
    
    arc_r = wr + 4
    
    bp = []
    
    bp.append((xl, bb_y))
    bp.append((xl, fb_top_y))
    
    c1x = xl + 15
    c1y = hl_y - 12
    bp.append(("Q", c1x, c1y, hx_start, hl_y))
    
    bp.append((fx_wall - 8, hl_y))
    
    c2x = fx_wall
    c2y = hl_y + 2
    bp.append(("Q", c2x, c2y, ws_bot_x, hl_y + 6))
    
    bp.append((ws_top_x, ws_top_y))
    bp.append((rs_x1, rt_y))
    bp.append((rs_x2, rt_y))
    bp.append((rdeck_x2, rdeck_y))
    
    c3x = xr - 18
    c3y = rdeck_final_y
    bp.append(("Q", c3x, c3y, xr, rb_top_y))
    
    bp.append((xr, bb_y))
    
    w2as_x = w2x + arc_r
    w2as_y = bb_y
    w2ae_x = w2x - arc_r
    w2ae_y = bb_y
    
    q1cx = w2as_x + 5
    q1cy = bb_y + 0.5
    bp.append(("Q", q1cx, q1cy, w2as_x, w2as_y))
    bp.append(("A", arc_r, arc_r, 0, 0, 0, w2ae_x, w2ae_y))
    
    mid1 = (w2ae_x + (w1x + arc_r)) / 2
    bp.append(("Q", mid1, bb_y + 0.5, w1x + arc_r, bb_y))
    
    w1as_x = w1x + arc_r
    w1ae_x = w1x - arc_r
    bp.append(("A", arc_r, arc_r, 0, 0, 0, w1ae_x, bb_y))
    
    q2cx = w1ae_x - 5
    q2cy = bb_y + 0.5
    bp.append(("Q", q2cx, q2cy, xl, bb_y))
    bp.append(("Z",))
    
    body_path = build_path(bp)
    
    gm = 5
    gp = []
    
    g1x = ws_bot_x + gm
    g1y = hl_y + gm + 2
    gp.append((g1x, g1y))
    
    g2x = ws_top_x + 2
    g2y = ws_top_y + gm
    gp.append((g2x, g2y))
    
    g3x = rs_x1 + 2
    g3y = rt_y + gm
    gp.append((g3x, g3y))
    
    g4x = rs_x2 - 2
    g4y = rt_y + gm
    gp.append((g4x, g4y))
    
    g5x = rdeck_x2 - gm
    g5y = rdeck_y + gm
    gp.append((g5x, g5y))
    
    rg_dx = rws_dx * 0.45
    rg6x = rws_bot_x - rg_dx
    rg6y = bb_y - (hh * 0.75)
    gp.append((rg6x, rg6y))
    
    fg_dx = ws_dx * 0.18
    fg7x = fx_wall + fg_dx
    fg7y = hl_y + gm + 4
    gp.append((fg7x, fg7y))
    gp.append(("Z",))
    
    glass_path = build_path(gp)
    
    bpil_x = rs_x1 + (rs_x2 - rs_x1) * 0.5
    bpil_top_y = rt_y + gm
    bpil_bot_y = rg6y - 2
    
    gt = adjust_brightness(brand_color, 0.95)
    gb = adjust_brightness(brand_color, 0.55)
    
    glt = adjust_brightness(brand_color, 0.45)
    glb = adjust_brightness(brand_color, 0.2)
    
    sh_cx = cx
    sh_cy = ground_y + 9
    sh_rx = L * 0.47
    sh_ry = 9
    
    gid = car['model_key'].replace('-', '').replace('911', 'nine')
    
    wb_r1 = wr * 0.70
    wb_r2 = wr * 0.30
    wb_r3 = wr * 0.10
    
    svg_parts = []
    svg_parts.append(f'<svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">')
    svg_parts.append(f'  <defs>')
    svg_parts.append(f'    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append(f'      <stop offset="0%" stop-color="#0f172a"/>')
    svg_parts.append(f'      <stop offset="100%" stop-color="#1e293b"/>')
    svg_parts.append(f'    </linearGradient>')
    svg_parts.append(f'    <linearGradient id="body{gid}" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append(f'      <stop offset="0%" stop-color="{gt}"/>')
    svg_parts.append(f'      <stop offset="100%" stop-color="{gb}"/>')
    svg_parts.append(f'    </linearGradient>')
    svg_parts.append(f'    <linearGradient id="glass{gid}" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append(f'      <stop offset="0%" stop-color="{glt}" stop-opacity="0.92"/>')
    svg_parts.append(f'      <stop offset="100%" stop-color="{glb}" stop-opacity="0.92"/>')
    svg_parts.append(f'    </linearGradient>')
    svg_parts.append(f'    <radialGradient id="rim{gid}" cx="50%" cy="50%" r="50%">')
    svg_parts.append(f'      <stop offset="0%" stop-color="#94a3b8"/>')
    svg_parts.append(f'      <stop offset="55%" stop-color="#475569"/>')
    svg_parts.append(f'      <stop offset="100%" stop-color="#1e293b"/>')
    svg_parts.append(f'    </radialGradient>')
    svg_parts.append(f'  </defs>')
    svg_parts.append(f'  <rect x="0" y="0" width="800" height="400" fill="url(#bgGrad)"/>')
    svg_parts.append(f'  <ellipse cx="{sh_cx:.2f}" cy="{sh_cy:.2f}" rx="{sh_rx:.2f}" ry="{sh_ry:.2f}" fill="#000" opacity="0.3"/>')
    svg_parts.append(f'  <path d="{body_path}" fill="url(#body{gid})" stroke="{brand_color}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>')
    svg_parts.append(f'  <path d="{glass_path}" fill="url(#glass{gid})" stroke="{adjust_brightness(brand_color, 0.65)}" stroke-width="1" opacity="0.92"/>')
    svg_parts.append(f'  <line x1="{bpil_x:.2f}" y1="{bpil_top_y:.2f}" x2="{bpil_x+2:.2f}" y2="{bpil_bot_y:.2f}" stroke="{adjust_brightness(brand_color, 0.55)}" stroke-width="1.5" opacity="0.7"/>')
    
    for wx in [w1x, w2x]:
        svg_parts.append(f'  <circle cx="{wx:.2f}" cy="{wy:.2f}" r="{wr:.2f}" fill="#020617" stroke="#000" stroke-width="2"/>')
        svg_parts.append(f'  <circle cx="{wx:.2f}" cy="{wy:.2f}" r="{wb_r1:.2f}" fill="url(#rim{gid})" stroke="#475569" stroke-width="1.2"/>')
        svg_parts.append(f'  <circle cx="{wx:.2f}" cy="{wy:.2f}" r="{wb_r2:.2f}" fill="#0f172a" stroke="#64748b" stroke-width="1.2"/>')
        svg_parts.append(f'  <circle cx="{wx:.2f}" cy="{wy:.2f}" r="{wb_r3:.2f}" fill="{brand_color}" opacity="0.85"/>')
    
    label_brand = car['brand_key'].title().replace('-', ' ')
    svg_parts.append(f'  <text x="776" y="386" text-anchor="end" font-family="Courier New, monospace" font-size="13" fill="{brand_color}" font-weight="bold">')
    svg_parts.append(f'    {label_brand} - {car["model_name"]}  L:{p["overall_length"]}mm')
    svg_parts.append(f'  </text>')
    svg_parts.append(f'</svg>')
    
    return "\n".join(svg_parts)

def build_path(points):
    parts = []
    started = False
    for pt in points:
        if not isinstance(pt, tuple):
            continue
        if pt[0] == "Z":
            parts.append("Z")
        elif pt[0] == "Q" and len(pt) == 5:
            _, cx1, cy1, x, y = pt
            parts.append(f"Q {cx1:.2f} {cy1:.2f} {x:.2f} {y:.2f}")
        elif pt[0] == "A" and len(pt) == 8:
            _, rx, ry, rot, l, sw, x, y = pt
            parts.append(f"A {rx:.2f} {ry:.2f} {rot} {l} {sw} {x:.2f} {y:.2f}")
        elif pt[0] == "M" and len(pt) == 3:
            _, x, y = pt
            parts.append(f"M {x:.2f} {y:.2f}")
            started = True
        elif len(pt) == 2 and all(isinstance(v, (int, float)) for v in pt):
            x, y = pt
            if not started:
                parts.append(f"M {x:.2f} {y:.2f}")
                started = True
            else:
                parts.append(f"L {x:.2f} {y:.2f}")
    return " ".join(parts)

def main():
    count = 0
    for car in CARS:
        bd = os.path.join(BASE_PATH, car["brand_key"])
        os.makedirs(bd, exist_ok=True)
        fp = os.path.join(bd, f"{car['model_key']}.svg")
        c = generate_car_svg(car)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(c)
        print(f"OK: {fp}")
        count += 1
    print(f"\nDone. {count} files created.")

if __name__ == "__main__":
    main()
