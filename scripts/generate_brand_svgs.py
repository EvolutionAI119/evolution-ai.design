#!/usr/bin/env python3
import math
import os
import re
import xml.etree.ElementTree as ET

svgWidth = 800
svgHeight = 400
offsetX = 50
groundLineY = 350
dimTextY = 385

BRAND_COLORS = {
    'rolls-royce': '#4ade80',
    'bentley': '#3b82f6',
    'bugatti': '#f59e0b',
    'porsche': '#ef4444',
    'ferrari': '#dc2626',
}

CARS = [
    ('rolls-royce', 'phantom', 'Phantom', {
        'overall_length': 5770, 'overall_width': 2018, 'overall_height': 1648,
        'wheel_base': 3552, 'track_width': 1680, 'ground_clearance': 150,
        'hood_length': 1300, 'roof_height': 750, 'wheel_diameter': 750,
        'windshield_angle': 28, 'rear_window_angle': 22, 'rear_slant_angle': 12,
        'front_overhang': 1050, 'rear_overhang': 1168
    }),
    ('rolls-royce', 'ghost', 'Ghost', {
        'overall_length': 5546, 'overall_width': 1948, 'overall_height': 1550,
        'wheel_base': 3295, 'track_width': 1640, 'ground_clearance': 145,
        'hood_length': 1200, 'roof_height': 650, 'wheel_diameter': 720,
        'windshield_angle': 30, 'rear_window_angle': 24, 'rear_slant_angle': 14,
        'front_overhang': 1020, 'rear_overhang': 1231
    }),
    ('rolls-royce', 'cullinan', 'Cullinan', {
        'overall_length': 5341, 'overall_width': 2000, 'overall_height': 1835,
        'wheel_base': 3295, 'track_width': 1680, 'ground_clearance': 215,
        'hood_length': 1200, 'roof_height': 900, 'wheel_diameter': 780,
        'windshield_angle': 26, 'rear_window_angle': 20, 'rear_slant_angle': 10,
        'front_overhang': 970, 'rear_overhang': 1076
    }),
    ('rolls-royce', 'wraith', 'Wraith', {
        'overall_length': 5285, 'overall_width': 1947, 'overall_height': 1507,
        'wheel_base': 3112, 'track_width': 1630, 'ground_clearance': 135,
        'hood_length': 1400, 'roof_height': 550, 'wheel_diameter': 710,
        'windshield_angle': 38, 'rear_window_angle': 32, 'rear_slant_angle': 35,
        'front_overhang': 1090, 'rear_overhang': 1083
    }),
    ('bentley', 'continental-gt', 'Conti GT', {
        'overall_length': 4850, 'overall_width': 1954, 'overall_height': 1405,
        'wheel_base': 2851, 'track_width': 1650, 'ground_clearance': 125,
        'hood_length': 1450, 'roof_height': 480, 'wheel_diameter': 730,
        'windshield_angle': 38, 'rear_window_angle': 33, 'rear_slant_angle': 38,
        'front_overhang': 1000, 'rear_overhang': 999
    }),
    ('bentley', 'continental-gtc', 'Conti GTC', {
        'overall_length': 4850, 'overall_width': 1954, 'overall_height': 1405,
        'wheel_base': 2851, 'track_width': 1650, 'ground_clearance': 125,
        'hood_length': 1450, 'roof_height': 480, 'wheel_diameter': 730,
        'windshield_angle': 38, 'rear_window_angle': 33, 'rear_slant_angle': 38,
        'front_overhang': 1000, 'rear_overhang': 999
    }),
    ('bentley', 'flying-spur', 'Flying Spur', {
        'overall_length': 5316, 'overall_width': 1978, 'overall_height': 1484,
        'wheel_base': 3194, 'track_width': 1660, 'ground_clearance': 140,
        'hood_length': 1300, 'roof_height': 600, 'wheel_diameter': 730,
        'windshield_angle': 32, 'rear_window_angle': 26, 'rear_slant_angle': 16,
        'front_overhang': 1060, 'rear_overhang': 1062
    }),
    ('bentley', 'bentayga', 'Bentayga', {
        'overall_length': 5125, 'overall_width': 1998, 'overall_height': 1742,
        'wheel_base': 2995, 'track_width': 1680, 'ground_clearance': 200,
        'hood_length': 1200, 'roof_height': 850, 'wheel_diameter': 760,
        'windshield_angle': 28, 'rear_window_angle': 22, 'rear_slant_angle': 12,
        'front_overhang': 1030, 'rear_overhang': 1100
    }),
    ('bugatti', 'chiron', 'Chiron', {
        'overall_length': 4544, 'overall_width': 2038, 'overall_height': 1212,
        'wheel_base': 2711, 'track_width': 1720, 'ground_clearance': 95,
        'hood_length': 1550, 'roof_height': 320, 'wheel_diameter': 740,
        'windshield_angle': 48, 'rear_window_angle': 42, 'rear_slant_angle': 52,
        'front_overhang': 920, 'rear_overhang': 913
    }),
    ('bugatti', 'veyron', 'Veyron', {
        'overall_length': 4462, 'overall_width': 1998, 'overall_height': 1159,
        'wheel_base': 2710, 'track_width': 1710, 'ground_clearance': 90,
        'hood_length': 1500, 'roof_height': 300, 'wheel_diameter': 720,
        'windshield_angle': 46, 'rear_window_angle': 40, 'rear_slant_angle': 50,
        'front_overhang': 900, 'rear_overhang': 852
    }),
    ('bugatti', 'divo', 'Divo', {
        'overall_length': 4579, 'overall_width': 2038, 'overall_height': 1212,
        'wheel_base': 2711, 'track_width': 1730, 'ground_clearance': 90,
        'hood_length': 1550, 'roof_height': 310, 'wheel_diameter': 740,
        'windshield_angle': 50, 'rear_window_angle': 44, 'rear_slant_angle': 55,
        'front_overhang': 930, 'rear_overhang': 938
    }),
    ('porsche', '911', '911 Carrera', {
        'overall_length': 4519, 'overall_width': 1852, 'overall_height': 1299,
        'wheel_base': 2450, 'track_width': 1580, 'ground_clearance': 105,
        'hood_length': 1100, 'roof_height': 400, 'wheel_diameter': 680,
        'windshield_angle': 42, 'rear_window_angle': 35, 'rear_slant_angle': 45,
        'front_overhang': 920, 'rear_overhang': 1149
    }),
    ('porsche', 'taycan', 'Taycan', {
        'overall_length': 4963, 'overall_width': 1966, 'overall_height': 1381,
        'wheel_base': 2900, 'track_width': 1660, 'ground_clearance': 125,
        'hood_length': 1200, 'roof_height': 500, 'wheel_diameter': 710,
        'windshield_angle': 38, 'rear_window_angle': 32, 'rear_slant_angle': 35,
        'front_overhang': 980, 'rear_overhang': 1083
    }),
    ('porsche', 'panamera', 'Panamera', {
        'overall_length': 5049, 'overall_width': 1937, 'overall_height': 1423,
        'wheel_base': 2950, 'track_width': 1650, 'ground_clearance': 130,
        'hood_length': 1300, 'roof_height': 550, 'wheel_diameter': 710,
        'windshield_angle': 35, 'rear_window_angle': 28, 'rear_slant_angle': 30,
        'front_overhang': 1020, 'rear_overhang': 1079
    }),
    ('porsche', 'cayenne', 'Cayenne', {
        'overall_length': 4926, 'overall_width': 1983, 'overall_height': 1673,
        'wheel_base': 2895, 'track_width': 1680, 'ground_clearance': 190,
        'hood_length': 1200, 'roof_height': 780, 'wheel_diameter': 760,
        'windshield_angle': 28, 'rear_window_angle': 22, 'rear_slant_angle': 15,
        'front_overhang': 950, 'rear_overhang': 1081
    }),
    ('porsche', 'macan', 'Macan', {
        'overall_length': 4686, 'overall_width': 1923, 'overall_height': 1624,
        'wheel_base': 2807, 'track_width': 1650, 'ground_clearance': 180,
        'hood_length': 1150, 'roof_height': 720, 'wheel_diameter': 730,
        'windshield_angle': 30, 'rear_window_angle': 24, 'rear_slant_angle': 18,
        'front_overhang': 900, 'rear_overhang': 979
    }),
    ('ferrari', 'sf90', 'SF90 Stradale', {
        'overall_length': 4710, 'overall_width': 1972, 'overall_height': 1186,
        'wheel_base': 2650, 'track_width': 1700, 'ground_clearance': 90,
        'hood_length': 1450, 'roof_height': 300, 'wheel_diameter': 730,
        'windshield_angle': 50, 'rear_window_angle': 45, 'rear_slant_angle': 55,
        'front_overhang': 980, 'rear_overhang': 1080
    }),
    ('ferrari', 'f8-tributo', 'F8 Tributo', {
        'overall_length': 4611, 'overall_width': 1979, 'overall_height': 1206,
        'wheel_base': 2650, 'track_width': 1700, 'ground_clearance': 95,
        'hood_length': 1400, 'roof_height': 320, 'wheel_diameter': 720,
        'windshield_angle': 48, 'rear_window_angle': 42, 'rear_slant_angle': 52,
        'front_overhang': 950, 'rear_overhang': 1011
    }),
    ('ferrari', 'roma', 'Roma', {
        'overall_length': 4656, 'overall_width': 1974, 'overall_height': 1301,
        'wheel_base': 2670, 'track_width': 1680, 'ground_clearance': 105,
        'hood_length': 1350, 'roof_height': 420, 'wheel_diameter': 710,
        'windshield_angle': 40, 'rear_window_angle': 34, 'rear_slant_angle': 40,
        'front_overhang': 970, 'rear_overhang': 1016
    }),
]


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgba(hex_color, alpha):
    r, g, b = hex_to_rgb(hex_color)
    return f'rgba({r},{g},{b},{alpha})'


def extract_path_y_values(path_d):
    nums = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', path_d)
    nums = [float(n) for n in nums]
    ys = []
    tokens = re.findall(r'[MLQCZ]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', path_d, re.IGNORECASE)
    i = 0
    while i < len(tokens):
        t = tokens[i].upper()
        if t in ('M', 'L') and i + 2 < len(tokens):
            try:
                ys.append(float(tokens[i+2]))
            except (ValueError, IndexError):
                pass
            i += 3
        elif t == 'Q' and i + 4 < len(tokens):
            try:
                ys.append(float(tokens[i+2]))
                ys.append(float(tokens[i+4]))
            except (ValueError, IndexError):
                pass
            i += 5
        elif t == 'Z':
            i += 1
        else:
            i += 1
    return ys


def extract_circle_cy(svg_content):
    matches = re.findall(r'<circle[^>]*cy="([^"]+)"', svg_content)
    return [float(m) for m in matches]


def generate_svg(brand_key, model_key, model_name, params, brand_color):
    FO = params['front_overhang']
    RO = params['rear_overhang']
    WB = params['wheel_base']
    overall_length_from_parts = FO + WB + RO
    actualLength = overall_length_from_parts
    scale = (svgWidth - offsetX * 2) / actualLength

    def s(val):
        return val * scale

    frontX = 0
    rearX = s(actualLength)
    frontWheelX = s(FO)
    rearWheelX = s(FO + WB)
    wheelRadius = s(params['wheel_diameter'] / 2)
    ground_clearance = s(params['ground_clearance'])

    groundClearanceLine_Y = groundLineY - ground_clearance
    beltLineY = groundClearanceLine_Y - s(params['overall_height'] * 0.76)
    hoodLineY = groundClearanceLine_Y - s(params['overall_height'] * 0.62)
    trunkLineY = groundClearanceLine_Y - s(params['overall_height'] * 0.66)
    roofTopY = groundClearanceLine_Y - s(params['overall_height'])

    hoodEndX = s(params['hood_length'])
    trunkLength = min(s(RO * 0.6), s(params['hood_length'] * 0.5))
    trunkStartX = rearX - trunkLength
    windshieldAngleRad = params['windshield_angle'] * math.pi / 180
    rearWindowAngleRad = params['rear_window_angle'] * math.pi / 180
    rearSlantAngleRad = params['rear_slant_angle'] * math.pi / 180
    windshieldHeight = beltLineY - roofTopY
    windshieldTopX = hoodEndX + windshieldHeight / math.tan(windshieldAngleRad)
    maxRoofLength = trunkStartX - windshieldTopX
    slantFactor = min(max(params['rear_slant_angle'] / 60, 0), 1)
    roofLen = max(maxRoofLength * (1 - slantFactor * 0.6), s(800))
    rearWindowTopX = windshieldTopX + roofLen
    rearWindowVertHeight = beltLineY - roofTopY
    rearWindowHeightRatio = 0.5 + slantFactor * 0.35
    rearWindowHeight = rearWindowVertHeight * rearWindowHeightRatio
    rearWindowBottomX = rearWindowTopX + rearWindowHeight / math.tan(rearWindowAngleRad)

    underY = groundClearanceLine_Y - 4

    hoodQMidX = frontX + (hoodEndX - frontX) * 0.5
    trunkQMidX = rearWindowBottomX + (rearX - rearWindowBottomX) * 0.5

    bodyHeightPx = s(params['overall_height'])

    body_d = (
        # ① Front bumper bottom
        f"M{frontX + offsetX},{groundClearanceLine_Y} "
        # ② Front fender: smooth quadratic from ground level up to hood level
        #    Control point at 35% of front overhang, ~40% of body height above ground
        f"Q{frontX + offsetX + s(FO) * 0.35},{groundClearanceLine_Y - bodyHeightPx * 0.40} "
        f"{frontX + offsetX + s(FO) * 0.85},{hoodLineY} "
        # ③ Hood (flat to hoodEndX)
        f"L{hoodEndX + offsetX},{hoodLineY} "
        # ④ A-pillar base (drop to beltLineY)
        f"L{hoodEndX + offsetX},{beltLineY} "
        # ⑤ Windshield up to roof
        f"L{windshieldTopX + offsetX},{roofTopY} "
        # ⑥ Roof line
        f"L{rearWindowTopX + offsetX},{roofTopY} "
        # ⑦ C-pillar down to belt line
        f"L{rearWindowBottomX + offsetX},{beltLineY} "
        # ⑧ Trunk deck
        f"L{rearWindowBottomX + offsetX},{trunkLineY} "
        # ⑨ Rear fender: smooth quadratic from trunk level down to bumper
        #    Control point at 65% of rear overhang from trunk, 23% of body height below trunk
        f"Q{rearX + offsetX - s(RO) * 0.85},{trunkLineY + bodyHeightPx * 0.23} "
        f"{rearX + offsetX - s(RO) * 0.4},{groundClearanceLine_Y - bodyHeightPx * 0.08} "
        # ⑩ Rear bumper bottom
        f"L{rearX + offsetX},{groundClearanceLine_Y} "
        # ⑪ Underbody with wheel arches (semicircular cutouts for wheels)
        f"L{rearWheelX + offsetX + wheelRadius + 5},{underY} "
        f"Q{rearWheelX + offsetX},{underY + wheelRadius * 1.1} {rearWheelX + offsetX - wheelRadius - 5},{underY} "
        f"L{frontWheelX + offsetX + wheelRadius + 5},{underY} "
        f"Q{frontWheelX + offsetX},{underY + wheelRadius * 1.1} {frontWheelX + offsetX - wheelRadius - 5},{underY} "
        f"L{frontX + offsetX},{underY} "
        f"Z"
    )

    window_d = (
        f"M{hoodEndX + offsetX},{beltLineY} "
        f"L{windshieldTopX + offsetX},{roofTopY} "
        f"L{rearWindowTopX + offsetX},{roofTopY} "
        f"L{rearWindowBottomX + offsetX},{beltLineY} "
        f"Z"
    )

    shadowCx = offsetX + (frontX + rearX) / 2
    shadowCy = groundLineY + 8
    shadowRx = s(actualLength * 0.48)
    shadowRy = 7

    frontWheelCx = offsetX + s(FO)
    rearWheelCx = offsetX + s(FO + WB)
    wheelCenterY = groundLineY - wheelRadius

    rim_r = wheelRadius * 0.55
    hub_r = wheelRadius * 0.22
    dot_r = wheelRadius * 0.09

    grad_id_body = f'gradBody_{brand_key}_{model_key}'
    grad_id_window = f'gradWindow_{brand_key}_{model_key}'
    grad_id_bg = f'gradBg_{brand_key}_{model_key}'
    grad_id_shadow = f'gradShadow_{brand_key}_{model_key}'
    grad_id_rim = f'gradRim_{brand_key}_{model_key}'

    footer_text = f"{brand_key.title()} - {model_name}  L:{params['overall_length']}mm"

    svg_parts = []
    svg_parts.append(f'<?xml version="1.0" encoding="UTF-8"?>')
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svgWidth}" height="{svgHeight}" viewBox="0 0 {svgWidth} {svgHeight}">')
    svg_parts.append(f'  <defs>')
    svg_parts.append(f'    <linearGradient id="{grad_id_bg}" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append(f'      <stop offset="0%" style="stop-color:#0f172a;stop-opacity:1" />')
    svg_parts.append(f'      <stop offset="100%" style="stop-color:#1e293b;stop-opacity:1" />')
    svg_parts.append(f'    </linearGradient>')
    svg_parts.append(f'    <linearGradient id="{grad_id_body}" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append(f'      <stop offset="0%" style="stop-color:{brand_color};stop-opacity:0.95" />')
    svg_parts.append(f'      <stop offset="100%" style="stop-color:{brand_color};stop-opacity:0.5" />')
    svg_parts.append(f'    </linearGradient>')
    svg_parts.append(f'    <linearGradient id="{grad_id_window}" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append(f'      <stop offset="0%" style="stop-color:#1e3a5f;stop-opacity:0.92" />')
    svg_parts.append(f'      <stop offset="100%" style="stop-color:#0f172a;stop-opacity:0.92" />')
    svg_parts.append(f'    </linearGradient>')
    svg_parts.append(f'    <radialGradient id="{grad_id_shadow}" cx="50%" cy="50%" r="50%">')
    svg_parts.append(f'      <stop offset="0%" style="stop-color:#000000;stop-opacity:0.5" />')
    svg_parts.append(f'      <stop offset="100%" style="stop-color:#000000;stop-opacity:0" />')
    svg_parts.append(f'    </radialGradient>')
    svg_parts.append(f'    <linearGradient id="{grad_id_rim}" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg_parts.append(f'      <stop offset="0%" style="stop-color:#e2e8f0;stop-opacity:1" />')
    svg_parts.append(f'      <stop offset="50%" style="stop-color:#94a3b8;stop-opacity:1" />')
    svg_parts.append(f'      <stop offset="100%" style="stop-color:#64748b;stop-opacity:1" />')
    svg_parts.append(f'    </linearGradient>')
    svg_parts.append(f'  </defs>')

    svg_parts.append(f'  <rect width="{svgWidth}" height="{svgHeight}" fill="url(#{grad_id_bg})" />')
    svg_parts.append(f'  <ellipse cx="{shadowCx}" cy="{shadowCy}" rx="{shadowRx}" ry="{shadowRy}" fill="url(#{grad_id_shadow})" />')
    svg_parts.append(f'  <line x1="20" y1="{groundLineY + 1}" x2="780" y2="{groundLineY + 1}" stroke="{rgba(brand_color, 0.3)}" stroke-width="1" />')

    svg_parts.append(f'  <path d="{body_d}" fill="url(#{grad_id_body})" stroke="{brand_color}" stroke-width="1.5" stroke-linejoin="round" />')
    svg_parts.append(f'  <path d="{window_d}" fill="url(#{grad_id_window})" stroke="{rgba(brand_color, 0.6)}" stroke-width="0.6" stroke-linejoin="round" />')

    for wheelCx in [frontWheelCx, rearWheelCx]:
        svg_parts.append(f'  <circle cx="{wheelCx}" cy="{wheelCenterY}" r="{wheelRadius}" fill="#020617" stroke="#000000" stroke-width="2" />')
        svg_parts.append(f'  <circle cx="{wheelCx}" cy="{wheelCenterY}" r="{rim_r}" fill="url(#{grad_id_rim})" stroke="#334155" stroke-width="1" />')
        svg_parts.append(f'  <circle cx="{wheelCx}" cy="{wheelCenterY}" r="{hub_r}" fill="#1e293b" stroke="#0f172a" stroke-width="0.5" />')
        svg_parts.append(f'  <circle cx="{wheelCx}" cy="{wheelCenterY}" r="{dot_r}" fill="{brand_color}" />')

    svg_parts.append(f'  <text x="776" y="{dimTextY}" text-anchor="end" fill="{brand_color}" font-family="monospace" font-size="13" font-weight="bold">{footer_text}</text>')
    svg_parts.append(f'</svg>')

    return '\n'.join(svg_parts)


def validate_xml(file_path):
    try:
        ET.parse(file_path)
        return True
    except ET.ParseError:
        return False


def main():
    base_dir = r'd:\API\Evolution-Ai.Design\public\brands'
    results = []
    ghost_info = {}

    for brand_key, model_key, model_name, params in CARS:
        brand_color = BRAND_COLORS[brand_key]
        svg_content = generate_svg(brand_key, model_key, model_name, params, brand_color)

        brand_dir = os.path.join(base_dir, brand_key)
        os.makedirs(brand_dir, exist_ok=True)

        file_path = os.path.join(brand_dir, f'{model_key}.svg')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)

        file_size = os.path.getsize(file_path)
        xml_valid = validate_xml(file_path)
        file_exists = os.path.exists(file_path)

        if brand_key == 'rolls-royce' and model_key == 'ghost':
            body_match = re.search(r'<path[^>]*d="([^"]+)"[^>]*fill="url\(#gradBody_', svg_content)
            if body_match:
                ys = extract_path_y_values(body_match.group(1))
                if ys:
                    ghost_info['body_min_y'] = min(ys)
                    ghost_info['body_max_y'] = max(ys)
                    ghost_info['body_ys'] = sorted(set(round(y, 2) for y in ys))[:12]
                    ghost_info['path_ends_with_z'] = body_match.group(1).strip().upper().endswith('Z')
            wheel_cys = extract_circle_cy(svg_content)
            ghost_info['wheel_cys'] = wheel_cys

        results.append({
            'brand': brand_key,
            'model': model_key,
            'path': file_path,
            'size': file_size,
            'xml_valid': xml_valid,
            'file_exists': file_exists
        })

    print('\n' + '=' * 120)
    print(f'{"#":<3} {"品牌":<14} {"车型":<18} {"文件大小":<10} {"XML有效":<8} {"状态":<10} 文件路径')
    print('-' * 120)
    for i, r in enumerate(results, 1):
        ok = r['xml_valid'] and r['file_exists'] and r['size'] > 3072
        status = '✓ 有效' if ok else '✗ 异常'
        xml_str = '✓' if r['xml_valid'] else '✗'
        print(f'{i:<3} {r["brand"]:<14} {r["model"]:<18} {r["size"]:<10} {xml_str:<8} {status:<10} {r["path"]}')
    print('=' * 120)

    all_ok = all(r['xml_valid'] and r['file_exists'] and r['size'] > 3072 for r in results)
    all_exist = all(r['file_exists'] for r in results)
    all_xml_valid = all(r['xml_valid'] for r in results)
    print(f'\n总计: {len(results)} 个文件')
    print(f'全部文件路径存在: {"是" if all_exist else "否"}')
    print(f'全部XML有效: {"是" if all_xml_valid else "否"}')
    print(f'全部有效 (>3KB 且XML有效): {"是" if all_ok else "否"}')

    if all_ok:
        total_size = sum(r['size'] for r in results)
        print(f'总文件大小: {total_size} 字节 ({total_size / 1024:.1f} KB)')

    print('\n======= GHOST.SVG 验证 =======')
    if ghost_info:
        print(f'Body Y 范围: min={ghost_info.get("body_min_y", "?"):.2f}, max={ghost_info.get("body_max_y", "?"):.2f}')
        print(f'  (期望: min≈150, max≈330)')
        print(f'Body path 以 Z 闭合: {"✓" if ghost_info.get("path_ends_with_z") else "✗"}')
        wheel_cys = ghost_info.get('wheel_cys', [])
        print(f'Wheel circle CY 值: {[round(c,2) for c in wheel_cys]}')
        print(f'  (期望 ≈305, 即 350 - wheelRadius)')
    print('=' * 60)


if __name__ == '__main__':
    main()
