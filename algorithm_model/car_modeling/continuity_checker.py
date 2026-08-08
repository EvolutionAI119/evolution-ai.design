"""
continuity_checker - NURBS 曲面连续性检查器

封装 G0(位置连续) / G1(切线连续) 分析逻辑，支持：
  - 单对 / 批量曲面配对分析
  - TXT + CSV 报告输出
  - 设计意图验证（预期间隙 / 角度对比）
  - 可配置阈值与采样密度

核心算法：
  - 有限差分法向量 (evaluate_surface)
  - cKDTree 边界最近邻 + 4x4 边界组合最优匹配

用法示例::

    from algorithm_model.car_modeling import CarParams, ContinuityChecker
    from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
    from algorithm_model.car_modeling.body_ends_g1 import build_front_bumper_g1

    params = CarParams()
    body = build_body_nurbs(params)
    bumper = build_front_bumper_g1(params, body, g1_k=0.3, bulge=0.08)

    checker = ContinuityChecker()
    checker.add_surface("body", body)
    checker.add_surface("front_bumper", bumper)
    results = checker.analyze_all()
    checker.write_reports("data/step", prefix="my_check")
    print(checker.summary())
"""
import os
import csv
import numpy as np
from scipy.spatial import cKDTree

from algorithm_model.freeform.nurbs_core import evaluate_surface

# 默认阈值
_DEFAULT_G0_THRESH_MM = 0.1
_DEFAULT_G1_THRESH_DEG = 1.0
_DEFAULT_G1_VISUAL_DEG = 5.0
_DEFAULT_PAIR_SAMPLE = 50
_EDGES = ("u0", "u1", "v0", "v1")


class ContinuityChecker:
    """NURBS 曲面连续性检查器。

    Parameters
    ----------
    g0_thresh_mm : float
        G0 位置连续阈值 (mm)，默认 0.1mm
    g1_thresh_deg : float
        G1 切线连续阈值 (deg)，默认 1.0deg
    g1_visual_deg : float
        视觉平滑阈值 (deg)，默认 5.0deg
    n_samples : int
        每条边界采样点数，默认 50
    skip_patterns : list of str, optional
        名称包含这些模式的两曲面配对将被跳过
        (如 ["wheel_", "mirror_"] 跳过车轮/后视镜互相配对)
    """

    def __init__(self, g0_thresh_mm=_DEFAULT_G0_THRESH_MM,
                 g1_thresh_deg=_DEFAULT_G1_THRESH_DEG,
                 g1_visual_deg=_DEFAULT_G1_VISUAL_DEG,
                 n_samples=_DEFAULT_PAIR_SAMPLE,
                 skip_patterns=None):
        self.g0_thresh_mm = g0_thresh_mm
        self.g1_thresh_deg = g1_thresh_deg
        self.g1_visual_deg = g1_visual_deg
        self.n_samples = n_samples
        self.skip_patterns = skip_patterns or []

        self._items = []          # [(name, surf), ...]
        self._name_set = set()
        self._edge_cache = {}     # {name: {edge: (pts, normals, params)}}
        self._results = None      # analyze_all 后填充

    # ------------------------------------------------------------------
    # 曲面注册
    # ------------------------------------------------------------------
    def add_surface(self, name, surf):
        """添加单个曲面到检查集。

        Parameters
        ----------
        name : str
            曲面唯一名称
        surf : NURBSSurface
            NURBS 曲面对象
        """
        if name in self._name_set:
            raise ValueError("重复的曲面名称: %s" % name)
        self._items.append((name, surf))
        self._name_set.add(name)

    def add_surfaces(self, items):
        """批量添加曲面。

        Parameters
        ----------
        items : list of (str, NURBSSurface)
            或 list of (NURBSSurface, str, ...) 自动取前两列反转
        """
        for item in items:
            if isinstance(item[0], str):
                name, surf = item[0], item[1]
            else:
                surf, name = item[0], item[1]
            self.add_surface(name, surf)

    @property
    def items(self):
        """返回 (name, surf) 列表。"""
        return list(self._items)

    @property
    def results(self):
        """返回最近一次 analyze_all 的结果，未分析则返回 None。"""
        return self._results

    # ------------------------------------------------------------------
    # 核心分析
    # ------------------------------------------------------------------
    @staticmethod
    def surface_normal_fd(surf, u, v, h=1e-4):
        """有限差分计算曲面在 (u, v) 处的单位法向量。"""
        hu = hv = max(h, 1e-5)
        if u - hu < 0.0:
            su = (evaluate_surface(surf, u + hu, v) -
                  evaluate_surface(surf, u, v)) / hu
        elif u + hu > 1.0:
            su = (evaluate_surface(surf, u, v) -
                  evaluate_surface(surf, u - hu, v)) / hu
        else:
            su = (evaluate_surface(surf, u + hu, v) -
                  evaluate_surface(surf, u - hu, v)) / (2 * hu)

        if v - hv < 0.0:
            sv = (evaluate_surface(surf, u, v + hv) -
                  evaluate_surface(surf, u, v)) / hv
        elif v + hv > 1.0:
            sv = (evaluate_surface(surf, u, v) -
                  evaluate_surface(surf, u, v - hv)) / hv
        else:
            sv = (evaluate_surface(surf, u, v + hv) -
                  evaluate_surface(surf, u, v - hv)) / (2 * hv)

        n = np.cross(su, sv)
        norm = np.linalg.norm(n)
        if norm < 1e-12:
            return np.array([0.0, 0.0, 1.0])
        return n / norm

    def boundary_curve_points(self, surf, edge, n=None):
        """采样曲面某条边界的点坐标、法向量和参数。

        Parameters
        ----------
        surf : NURBSSurface
        edge : str  ("u0" | "u1" | "v0" | "v1")
        n : int, optional  采样点数，默认用 self.n_samples

        Returns
        -------
        pts : (n, 3) ndarray       边界点坐标
        normals : (n, 3) ndarray   边界点法向量
        params : (n, 2) ndarray    边界点 (u, v) 参数
        """
        if n is None:
            n = self.n_samples
        pts = np.zeros((n, 3))
        normals = np.zeros((n, 3))
        params = np.zeros((n, 2))
        for i, t in enumerate(np.linspace(0.0, 1.0, n)):
            if edge == "u0":
                u, v = 0.0, t
            elif edge == "u1":
                u, v = 1.0, t
            elif edge == "v0":
                u, v = t, 0.0
            else:
                u, v = t, 1.0
            pts[i] = evaluate_surface(surf, u, v)
            normals[i] = self.surface_normal_fd(surf, u, v)
            params[i] = [u, v]
        return pts, normals, params

    def _get_edges(self, name, surf):
        """获取（或缓存）曲面所有 4 条边界的采样数据。"""
        if name not in self._edge_cache:
            self._edge_cache[name] = {}
            for edge in _EDGES:
                pts, norms, params = self.boundary_curve_points(surf, edge)
                self._edge_cache[name][edge] = (pts, norms, params)
        return self._edge_cache[name]

    def _should_skip(self, name_a, name_b):
        """根据 skip_patterns 判断是否跳过该配对。"""
        for pat in self.skip_patterns:
            if pat in name_a and pat in name_b:
                return True
        return False

    def analyze_pair(self, name_a, name_b):
        """分析单个曲面对的 G0/G1 连续性。

        遍历 4x4=16 种边界组合，取最小间隙为最佳匹配。

        Returns
        -------
        dict  包含 min_gap_mm, max_g1_deg, rating 等字段
        """
        surf_a = dict(self._items)[name_a]
        surf_b = dict(self._items)[name_b]
        edges_a = self._get_edges(name_a, surf_a)
        edges_b = self._get_edges(name_b, surf_b)

        best = None
        for ea in _EDGES:
            pts_a, norms_a, _ = edges_a[ea]
            tree_a_yz = cKDTree(pts_a[:, 1:3])
            for eb in _EDGES:
                pts_b, norms_b, _ = edges_b[eb]
                tree_b_yz = cKDTree(pts_b[:, 1:3])

                dists_ab, idx_ab = tree_b_yz.query(pts_a[:, 1:3], k=1)
                dists_ba, idx_ba = tree_a_yz.query(pts_b[:, 1:3], k=1)
                min_gap = float(min(dists_ab.min(), dists_ba.min())) * 1000.0

                mask = dists_ab < (self.g0_thresh_mm / 1000.0 * 20)
                contact_g1 = []
                for k in np.where(mask)[0]:
                    pa = pts_a[k]
                    na = norms_a[k]
                    nb = norms_b[idx_ab[k]]
                    cos_a = float(np.clip(np.dot(na, nb), -1.0, 1.0))
                    ang = float(np.degrees(np.arccos(cos_a)))
                    if ang > 90.0:
                        ang = 180.0 - ang
                    contact_g1.append(
                        (ang, float(np.linalg.norm(pa - pts_b[idx_ab[k]])) * 1000.0))

                if not contact_g1:
                    small_idx = np.argsort(dists_ab)[:min(5, len(dists_ab))]
                    for k in small_idx:
                        na = norms_a[k]
                        nb = norms_b[idx_ab[k]]
                        cos_a = float(np.clip(np.dot(na, nb), -1.0, 1.0))
                        ang = float(np.degrees(np.arccos(cos_a)))
                        if ang > 90.0:
                            ang = 180.0 - ang
                        contact_g1.append((ang, dists_ab[k] * 1000.0))

                angs = np.array([c[0] for c in contact_g1])
                gaps_here = np.array([c[1] for c in contact_g1])

                cand = {
                    "min_gap_mm": min_gap,
                    "mean_g0_mm": float(gaps_here.mean()),
                    "max_g1_deg": float(angs.max()),
                    "mean_g1_deg": float(angs.mean()),
                    "best_edge_pair": ea + "<->" + eb,
                    "samples": len(contact_g1),
                }
                if best is None or cand["min_gap_mm"] < best["min_gap_mm"]:
                    best = cand

        r = {
            "pair": name_a + " <-> " + name_b,
            "label_a": name_a,
            "label_b": name_b,
            **best,
        }
        self._annotate_rating(r)
        return r

    def analyze_all(self):
        """批量分析所有已注册曲面对。

        Returns
        -------
        list of dict  按 min_gap_mm 升序排列
        """
        self._edge_cache.clear()
        results = []
        n = len(self._items)
        for i in range(n):
            name_a, surf_a = self._items[i]
            self._get_edges(name_a, surf_a)
            for j in range(i + 1, n):
                name_b, surf_b = self._items[j]
                if self._should_skip(name_a, name_b):
                    continue
                results.append(self.analyze_pair(name_a, name_b))

        results.sort(key=lambda r: r["min_gap_mm"])
        self._results = results
        return results

    def _annotate_rating(self, r):
        """为结果字典填充 g0_pass / g1_pass / rating 字段。"""
        r["g0_pass"] = bool(r["min_gap_mm"] < self.g0_thresh_mm)
        r["g1_pass"] = bool(r["max_g1_deg"] < self.g1_thresh_deg)
        r["visual_smooth"] = bool(r["max_g1_deg"] < self.g1_visual_deg)

        if r["g0_pass"] and r["g1_pass"]:
            r["rating"] = "G1 OK"
        elif r["g0_pass"] and r["visual_smooth"]:
            r["rating"] = "G0 OK"
        elif r["min_gap_mm"] < 1.0:
            r["rating"] = "Near G0"
        elif r["min_gap_mm"] < 10.0:
            r["rating"] = "Small gap"
        else:
            r["rating"] = "Separated"

    # ------------------------------------------------------------------
    # 报告输出
    # ------------------------------------------------------------------
    def write_reports(self, out_dir, prefix="continuity"):
        """输出 TXT + CSV 报告。

        Parameters
        ----------
        out_dir : str  输出目录
        prefix : str  文件名前缀

        Returns
        -------
        txt_path : str
        csv_path : str
        """
        if self._results is None:
            raise RuntimeError("请先调用 analyze_all()")

        os.makedirs(out_dir, exist_ok=True)
        txt_path = os.path.join(out_dir, prefix + "_report.txt")
        csv_path = os.path.join(out_dir, prefix + "_pairs.csv")

        # CSV
        headers = ["pair", "label_a", "label_b", "min_gap_mm", "mean_g0_mm",
                   "max_g1_deg", "mean_g1_deg", "best_edge_pair", "samples",
                   "g0_pass", "g1_pass", "visual_smooth", "rating"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            for r in self._results:
                w.writerow({k: r[k] for k in headers})

        # TXT
        lines = self._build_txt_report()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return txt_path, csv_path

    def _build_txt_report(self, design_checks=None):
        """构建 TXT 报告文本行列表。"""
        results = self._results
        n_surfs = len(self._items)
        sep = "=" * 78
        lines = [sep,
                 "NURBS Surface Continuity Report (ContinuityChecker)",
                 "  Surfaces: %d  |  Pairs: %d" % (n_surfs, len(results)),
                 "  Method: finite-diff normals + cKDTree boundary nearest neighbor",
                 "  Threshold: G0 < %.2fmm / G1 < %.1fdeg / Visual < %.1fdeg" % (
                     self.g0_thresh_mm, self.g1_thresh_deg, self.g1_visual_deg),
                 "  Samples per boundary: %d" % self.n_samples,
                 sep]

        # Summary table
        lines += ["", "[Summary] Sorted by min_gap ascending:", "-" * 90,
                  "%-40s %12s %12s %10s %8s" % (
                      "Pair", "min_gap(mm)", "max_g1(deg)", "contact%", "Rating"),
                  "-" * 90]
        for r in results:
            contact_pct = 100.0 * (1.0 if r["g0_pass"] else max(
                0.0, (self.g0_thresh_mm - r["min_gap_mm"]) /
                max(self.g0_thresh_mm, 1e-6)))
            lines.append("%-40s %12.3f %12.3f %9.1f%% %8s" % (
                r["pair"][:40], r["min_gap_mm"], r["max_g1_deg"],
                contact_pct, r["rating"]))
        lines.append("-" * 90)

        # Statistics
        total = len(results)
        g0_ok = sum(1 for r in results if r["g0_pass"])
        g1_ok = sum(1 for r in results if r["g1_pass"])
        both = sum(1 for r in results if r["g0_pass"] and r["g1_pass"])
        lines += ["", "[Statistics] Total pairs: %d" % total,
                  "  G0 pass: %d/%d  (%.1f%%)" % (
                      g0_ok, total, 100.0 * g0_ok / max(total, 1)),
                  "  G1 pass: %d/%d  (%.1f%%)" % (
                      g1_ok, total, 100.0 * g1_ok / max(total, 1)),
                  "  G0+G1:  %d/%d  (%.1f%%)" % (
                      both, total, 100.0 * both / max(total, 1))]

        # Detail top 15
        lines += ["", "[Detail] Top 15 closest pairs:", "=" * 78]
        for r in results[:15]:
            lines += ["", "* " + r["pair"],
                      "  best_edge=%s  samples=%d" % (
                          r["best_edge_pair"], r["samples"]),
                      "  G0: min=%.4fmm  mean=%.4fmm  pass=%s" % (
                          r["min_gap_mm"], r["mean_g0_mm"], r["g0_pass"]),
                      "  G1: max=%.3fdeg  mean=%.3fdeg  pass=%s  visual=%s" % (
                          r["max_g1_deg"], r["mean_g1_deg"],
                          r["g1_pass"], r["visual_smooth"]),
                      "  Rating: " + r["rating"]]

        # Design intent verification
        if design_checks:
            lines += ["", sep, "[Design Intent Verification]", "-" * 78]
            check_map = {r["pair"]: r for r in results}
            for entry in design_checks:
                pair, desc, expect_g0, expect_g1, want_g0, want_g1 = entry
                r = check_map.get(pair)
                if r is None:
                    a, b = pair.split(" <-> ")
                    r = check_map.get(b + " <-> " + a)
                if r is None:
                    lines.append("  [MISS] " + pair)
                    continue
                ok_g0 = "OK" if (abs(r["min_gap_mm"] - expect_g0) < 5.0 or
                                 (expect_g0 == 0.0 and
                                  r["min_gap_mm"] < self.g0_thresh_mm)) else "CHECK"
                if expect_g1 is not None:
                    ok_g1 = "OK" if (abs(r["max_g1_deg"] - expect_g1) <
                                     self.g1_thresh_deg * 2) else "CHECK"
                else:
                    ok_g1 = "N/A"
                lines.append("  [%s/%s] %s" % (ok_g0, ok_g1, pair))
                lines.append("      G0: %.4fmm (%s)  expect %s" % (
                    r["min_gap_mm"], want_g0, want_g0))
                lines.append("      G1: %.3fdeg  expect %s" % (
                    r["max_g1_deg"], want_g1))
                lines.append("      " + desc)

        lines += ["", sep]
        return lines

    def write_reports_with_design_checks(self, out_dir, design_checks,
                                         prefix="continuity"):
        """输出带设计意图验证的 TXT + CSV 报告。

        Parameters
        ----------
        out_dir : str
        design_checks : list of tuple
            每项为 (pair_str, desc, expect_g0_mm, expect_g1_deg_or_None,
                    want_g0_label, want_g1_label)
        prefix : str

        Returns
        -------
        txt_path, csv_path
        """
        if self._results is None:
            raise RuntimeError("请先调用 analyze_all()")

        os.makedirs(out_dir, exist_ok=True)
        txt_path = os.path.join(out_dir, prefix + "_report.txt")
        csv_path = os.path.join(out_dir, prefix + "_pairs.csv")

        headers = ["pair", "label_a", "label_b", "min_gap_mm", "mean_g0_mm",
                   "max_g1_deg", "mean_g1_deg", "best_edge_pair", "samples",
                   "g0_pass", "g1_pass", "visual_smooth", "rating"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            for r in self._results:
                w.writerow({k: r[k] for k in headers})

        lines = self._build_txt_report(design_checks=design_checks)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return txt_path, csv_path

    # ------------------------------------------------------------------
    # 查询辅助
    # ------------------------------------------------------------------
    def summary(self):
        """返回统计摘要字典。"""
        if self._results is None:
            return {"status": "not analyzed"}
        total = len(self._results)
        g0_ok = sum(1 for r in self._results if r["g0_pass"])
        g1_ok = sum(1 for r in self._results if r["g1_pass"])
        both = sum(1 for r in self._results if r["g0_pass"] and r["g1_pass"])
        ratings = {}
        for r in self._results:
            ratings[r["rating"]] = ratings.get(r["rating"], 0) + 1
        return {
            "total_pairs": total,
            "g0_pass": g0_ok,
            "g1_pass": g1_ok,
            "g0_g1_both": both,
            "g0_pass_pct": 100.0 * g0_ok / max(total, 1),
            "g1_pass_pct": 100.0 * g1_ok / max(total, 1),
            "rating_counts": ratings,
            "closest_pair": self._results[0]["pair"] if total else None,
            "closest_gap_mm": self._results[0]["min_gap_mm"] if total else None,
        }

    def get_pair(self, name_a, name_b):
        """查询指定配对的分析结果。

        Returns
        -------
        dict or None
        """
        if self._results is None:
            return None
        key1 = name_a + " <-> " + name_b
        key2 = name_b + " <-> " + name_a
        for r in self._results:
            if r["pair"] in (key1, key2):
                return r
        return None

    def filter_by_rating(self, rating):
        """按评级过滤结果。

        Parameters
        ----------
        rating : str  ("G1 OK" | "G0 OK" | "Near G0" | "Small gap" | "Separated")

        Returns
        -------
        list of dict
        """
        if self._results is None:
            return []
        return [r for r in self._results if r["rating"] == rating]
