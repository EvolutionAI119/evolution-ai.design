import urllib.request
import os
import struct

CAND_DIR = r"d:\API\Evolution-Ai.Design\public\_gtc_new_candidates"
BASE = "https://www.bentleymedia.com/image/{uid}?format=jpg&width=1920&quality=90"

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bentleymedia.com/",
    "Accept": "image/*,*/*;q=0.8",
}


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


results = []
for idx, uid in enumerate(UUIDS, 1):
    fname = "cand_%02d.jpg" % idx
    fpath = os.path.join(CAND_DIR, fname)
    url = BASE.format(uid=uid)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(fpath, "wb") as f:
            f.write(data)
        w, h = get_size(data)
        ratio = round(w / h, 2) if w and h else None
        kb = round(len(data) / 1024, 1)
        results.append((fname, w, h, ratio, kb))
        print("%s: %sx%s ratio=%s %sKB" % (fname, w, h, ratio, kb))
    except Exception as e:
        results.append((fname, None, None, None, str(e)))
        print("%s: ERROR %s" % (fname, e))

print("\n=== LANDSCAPE candidates (ratio 1.4-2.2) ===")
for fname, w, h, ratio, kb in results:
    if ratio and 1.4 <= ratio <= 2.2:
        print("  %s: %sx%s ratio=%s %sKB" % (fname, w, h, ratio, kb))
