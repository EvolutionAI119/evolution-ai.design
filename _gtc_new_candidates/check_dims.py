import os, struct, json

CAND_DIR = r"d:\API\Evolution-Ai.Design\public\_gtc_new_candidates"

def get_size(data):
    try:
        if data[:2] == b"\xff\xd8":
            i = 2
            n = len(data)
            while i < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                m = data[i + 1]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h = struct.unpack(">H", data[i + 5:i + 7])[0]
                    w = struct.unpack(">H", data[i + 7:i + 9])[0]
                    return w, h
                seg = struct.unpack(">H", data[i + 2:i + 4])[0]
                i += 2 + seg
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            w = struct.unpack(">I", data[16:20])[0]
            h = struct.unpack(">I", data[20:24])[0]
            return w, h
    except Exception:
        pass
    return None, None

UUIDS = [
    "60507731-7948-475e-9a90-ce425ce39d76",
    "3cc1e3ed-a0f7-455a-9472-f444e98b71fc",
    "86134ed8-a5f6-4b09-8bc3-c3b2a5c55e39",
    "021f39d3-1dde-4cb2-b9c6-1b6fd4407a11",
    "ca5765f6-0cc3-4546-ae9b-cce33362c3d6",
    "aca5fec8-34a5-4b4e-ad95-0f0b5d81e5ef",
    "ce8d15d5-892f-4893-b150-d479b8620b71",
    "07a6adbe-fc47-460b-a24a-101da3c3a4a1",
    "aecb19ea-7c2d-4fce-97b9-55aec5db7f89",
    "94f8df7c-df4f-47e1-9f48-4bf853e8798c",
    "409a1720-171a-4548-93f8-ca3a84f26f41",
    "2c29451d-6bff-45e8-b6db-923aeb3f9f27",
    "b3c0f6fa-632c-40ca-bac2-51e99f97d90d",
    "1d4b7e16-fbba-4f68-879e-d09fac4f9179",
    "46bbea58-b2ae-48fd-8c53-347c99f8004a",
    "343f67bf-c0c0-4157-9b55-4fc6214a0fac",
    "ee27913d-02e8-4163-b8da-ab8b6604ffca",
    "a985cff5-0d78-456d-9847-8ea98020f601",
    "bfec34cc-8e98-4836-a0f8-cb040a99ba3a",
    "796bc1b6-b79c-47bc-ae06-94958b8d6c77",
    "edb9621e-fb57-4247-8614-07b657ec380b",
    "c3b8a7cf-83a2-47ed-9d18-0c52556d85df",
]

results = []
for idx in range(1, 23):
    fname = "cand_%02d.jpg" % idx
    fpath = os.path.join(CAND_DIR, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, "rb") as f:
        data = f.read()
    w, h = get_size(data)
    kb = round(len(data) / 1024, 1)
    ratio = round(w / h, 2) if w and h else None
    uid = UUIDS[idx - 1] if idx - 1 < len(UUIDS) else ""
    cat = "landscape" if ratio and ratio >= 1.4 else ("portrait" if ratio and ratio < 1.0 else "square")
    results.append({"file": fname, "w": w, "h": h, "ratio": ratio, "kb": kb, "cat": cat, "uid": uid})

with open(os.path.join(CAND_DIR, "dims.json"), "w") as f:
    json.dump(results, f, indent=2)

print("DONE")
