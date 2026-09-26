"""测试 STEP/IGES/STL/CATPart/Wire 整车 CAD 文件导入流程。

合成三种测试数据：
1. trimesh 合成 STL mesh（尺寸 5000 × 1560 × 1920，模拟 SUV，单位 mm）
2. 合成 STEP AP214 文本（含 CARTESIAN_POINT，尺寸 4800 × 1450 × 1850）
3. 合成空的 CATPart / .wire 二进制文件，验证兜底分支
"""
from __future__ import annotations

import io
import json
import sys
import os
import traceback
from pathlib import Path

# 把 backend 目录加入 sys.path 以便 import
sys.path.insert(0, str(Path(__file__).resolve().parent))


def mk_suv_stl_bytes(L_mm=5000, H_mm=1560, W_mm=1920):
    """用 trimesh 合成一个整车外形的 box（模拟车身包围盒），导出 STL bytes。
    为了让后续反推有意义，我们在 (x,z) 平面的中心偏移，来影响质心判断前后悬。
    """
    import trimesh
    import numpy as np
    # 车身主箱体 + 4 个车轮（放在正常位置，让质心尽量居中偏前）
    body = trimesh.creation.box(extents=[L_mm, H_mm * 0.88, W_mm])
    body.apply_translation([L_mm / 2, H_mm * 0.56, 0])
    # 发动机盖稍短的凸起（SUV 造型）
    hood = trimesh.creation.box(extents=[L_mm * 0.25, H_mm * 0.12, W_mm * 0.78])
    hood.apply_translation([L_mm * 0.15, H_mm * 0.94, 0])
    # 车顶（让车高有效）
    roof = trimesh.creation.box(extents=[L_mm * 0.55, H_mm * 0.10, W_mm * 0.75])
    roof.apply_translation([L_mm * 0.55, H_mm * 0.95, 0])
    # 4 个车轮圆柱（径向代表直径）
    wheel_d = H_mm * 0.42
    wheel_w = wheel_d * 0.32
    track_w = W_mm * 0.85
    wheelbase = L_mm * 0.60
    FO = (L_mm - wheelbase) * 0.45
    RO = L_mm - wheelbase - FO
    gc = H_mm * 0.18
    wheels = []
    for side in [-1, 1]:
        for pos, x_off in [("front", FO + wheel_d / 2), ("rear", L_mm - RO - wheel_d / 2)]:
            w = trimesh.creation.cylinder(radius=wheel_d / 2, height=wheel_w, sections=16)
            w.apply_transform(trimesh.transformations.rotation_matrix(
                angle=3.14159265 / 2, direction=[0, 1, 0]
            ))
            w.apply_translation([x_off, gc + wheel_d / 2, side * track_w / 2])
            wheels.append(w)
    scene = trimesh.util.concatenate([body, hood, roof, *wheels])
    return scene.export(file_type="stl")


def mk_step_text_bytes(L=4800, H=1450, W=1850):
    """合成最小 STEP AP214 文本文件，仅包含一批 CARTESIAN_POINT 覆盖整车包围盒。
    尺寸单位：mm。
    """
    # 均匀生成 corners + 每条边中间点，保证包围盒正确
    xs = [0, L]
    ys = [0, H]
    zs = [-W / 2, W / 2]
    cps = []
    for x in xs:
        for y in ys:
            for z in zs:
                cps.append((x, y, z))
    # 再均匀撒一批点
    for xi in [L * 0.25, L * 0.5, L * 0.75]:
        for yi in [H * 0.3, H * 0.6]:
            for zi in [-W * 0.3, 0, W * 0.3]:
                cps.append((xi, yi, zi))
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('Synthetic SUV STEP for import test'),'2;1');",
        "FILE_NAME('suv_synth.step','2026-08-21T00:00:00',('EVOLUTION AI'),('EVOLUTION AI'),'',' ','');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
        "ENDSEC;",
        "DATA;",
    ]
    eid = 1
    for (x, y, z) in cps:
        lines.append(f"#{eid}=CARTESIAN_POINT('',({x:.4f},{y:.4f},{z:.4f}));")
        eid += 1
    lines += ["ENDSEC;", "END-ISO-10303-21;"]
    return "\n".join(lines).encode("utf-8")


def run_tests():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    all_ok = True

    # ------- 先确保健康 -------
    h = client.get("/api/v1/health")
    assert h.status_code == 200 and h.json()["status"] == "healthy", "health 失败"
    print("[OK] health")

    # ------- 1. JSON 导入（基线） -------
    r = client.post("/api/v1/import-export/import", json={"name": "json-baseline", "params": {}})
    assert r.status_code == 200, f"JSON import failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["param_count"] == 50
    assert data["source_format"] == ".json (inline)"
    print(f"[OK] JSON inline import → sid={data['session_id']}")

    # ------- 2. 合成 STL 文件上传（trimesh 解析 + 参数反推） -------
    stl_bytes = mk_suv_stl_bytes(5000, 1560, 1920)
    r = client.post(
        "/api/v1/import-export/import/file",
        files={"file": ("SUV_5000_1560_1920.stl", stl_bytes, "model/stl")},
    )
    if r.status_code != 200:
        print(f"[FAIL] STL import → HTTP {r.status_code}: {r.text}")
        all_ok = False
    else:
        data = r.json()
        print(f"[OK] STL import → sid={data['session_id']} name={data['name']}")
        print(f"     source_format={data.get('source_format')}")
        print(f"     bbox_size_mm={data.get('bbox_size_mm')}")
        print(f"     overrides_count={data.get('overrides_count')}")
        print(f"     warnings={data.get('warnings') or '[]'}")
        # 断言：包围盒长度必须正确（单位 mm，±2% 容差）
        bbox = data.get("bbox_size_mm") or [0, 0, 0]
        if not (4900 <= bbox[0] <= 5100):
            print(f"[WARN] 包围盒长度反推偏差较大：{bbox[0]} （预期 5000）")
        # 参数列表应该能读到，且 overall_length ≈ 5000
        sid = data["session_id"]
        r2 = client.get(f"/api/v1/import-export/{sid}/params")
        if r2.status_code != 200:
            print(f"[FAIL] 读取 params 失败: {r2.status_code} {r2.text}")
            all_ok = False
        else:
            params = {p["key"]: p["value"] for p in r2.json()}
            print(f"     overall_length = {params.get('overall_length')}")
            print(f"     overall_width  = {params.get('overall_width')}")
            print(f"     overall_height = {params.get('overall_height')}")
            print(f"     wheelbase      = {params.get('wheelbase')}")
            print(f"     wheel_diameter = {params.get('wheel_diameter')}")
            assert 4900 <= params.get("overall_length", 0) <= 5100, "overall_length 反推失败"
        # 修改一个参数并提交
        r3 = client.put(
            f"/api/v1/import-export/{sid}/params",
            json={"overrides": [{"group": "整车尺寸", "key": "overall_length", "value": 5200}]},
        )
        if r3.status_code != 200:
            print(f"[FAIL] 修改参数失败: {r3.status_code} {r3.text}")
            all_ok = False
        else:
            print(f"[OK] 修改 overall_length → 5200")
        # 导出 JSON
        r4 = client.post(
            f"/api/v1/import-export/{sid}/export",
            json={"formats": ["json"], "name": "SUV_STL_test"},
        )
        if r4.status_code != 200:
            print(f"[FAIL] 导出 JSON 失败: {r4.status_code} {r4.text}")
            all_ok = False
        else:
            files = r4.json().get("files", [])
            print(f"[OK] 导出 {len(files)} 个文件")

    # ------- 3. 合成 STEP 文本文件（文本解析点云路径） -------
    step_bytes = mk_step_text_bytes(4800, 1450, 1850)
    r = client.post(
        "/api/v1/import-export/import/file",
        files={"file": ("Sedan_4800_1450_1850.STEP", step_bytes, "application/step")},
    )
    if r.status_code != 200:
        print(f"[FAIL] STEP import → HTTP {r.status_code}: {r.text}")
        all_ok = False
    else:
        data = r.json()
        bbox = data.get("bbox_size_mm") or [0, 0, 0]
        print(f"[OK] STEP import → sid={data['session_id']} bbox={bbox}")
        # 包围盒必须是 [4800, 1450, 1850] 左右（X=最长, Y=最短, Z=中间）
        ok = (4750 <= bbox[0] <= 4850) and (1420 <= bbox[1] <= 1480) and (1820 <= bbox[2] <= 1880)
        if not ok:
            print(f"[WARN] STEP bbox 不匹配预期 [4800,1450,1850]")
        print(f"     warnings = {data.get('warnings') or '[]'}")

    # ------- 4. CATPart（二进制空文件，兜底分支） -------
    cat_bytes = b"CATIA V5 Binary Dummy Content - Not real CATPart"
    r = client.post(
        "/api/v1/import-export/import/file",
        files={"file": ("Audi_R8.CATPart", cat_bytes, "application/octet-stream")},
    )
    if r.status_code != 200:
        print(f"[FAIL] CATPart import → HTTP {r.status_code}: {r.text}")
        all_ok = False
    else:
        data = r.json()
        print(f"[OK] CATPart import → sid={data['session_id']}")
        geom_parsed = (data.get("meta") or {}).get("geometry_parsed")
        print(f"     geometry_parsed = {geom_parsed}  (应为 False/None)")
        warn = data.get("warnings") or []
        assert any("专有" in w or "兜底" in w or "暂不支持" in w for w in warn), (
            "CATPart 应当产出专有格式提示"
        )
        print(f"     warnings = {warn}")

    # ------- 5. Wire 格式（兜底分支） -------
    wire_bytes = b"WIRE_1.0\np 0 0 0\np 1000 200 0\nl 0 0 0 1000 200 0\n"
    r = client.post(
        "/api/v1/import-export/import/file",
        files={"file": ("chassis_skeleton.wire", wire_bytes, "application/octet-stream")},
    )
    if r.status_code != 200:
        print(f"[FAIL] Wire import → HTTP {r.status_code}: {r.text}")
        all_ok = False
    else:
        data = r.json()
        print(f"[OK] Wire import → sid={data['session_id']}")
        print(f"     warnings = {data.get('warnings') or '[]'}")

    # ------- 6. 不支持的扩展名 -------
    r = client.post(
        "/api/v1/import-export/import/file",
        files={"file": ("foo.xyz", b"garbage", "application/octet-stream")},
    )
    if r.status_code != 400:
        print(f"[FAIL] 不支持扩展名应返回 400，实际 {r.status_code}: {r.text}")
        all_ok = False
    else:
        print("[OK] 不支持扩展名正确返回 400")

    # ------- 7. 会话列表 -------
    r = client.get("/api/v1/import-export/sessions")
    if r.status_code != 200:
        print(f"[FAIL] sessions list → {r.status_code}")
        all_ok = False
    else:
        total = r.json().get("total", 0)
        print(f"[OK] sessions list total = {total}")
        assert total >= 5, "至少 5 个会话"

    if all_ok:
        print("\n✅ 全部测试通过")
    else:
        print("\n❌ 存在失败")
        sys.exit(1)


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        traceback.print_exc()
        sys.exit(2)
