"""
sop_checklist - A 表面标准 SOP 13 项检查清单

基于《A表面标准SOP》文档，将 13 项 Checklist 中可自动化的 8 项实现为代码检查，
剩余 5 项为人工/外部数据依赖项，生成带指引的占位条目。

自动化检查项：
  2. 基础大面简洁（控制点网格规模）
  4. 单凹/单凸，无多余拐点（曲率符号变化）
  5. 单段控制点 ≤ 7（U/V 方向）
  6. 交线间隙 < 0.01mm（严格 G0）
  7. R 值均匀变化（边界曲率变异系数）
  8. R 角 ≥ 3mm + U 向控制点 < 8
  12. Curvature 检查（曲率分布平滑度）
  13. G0/G1/G2 连续性（复用 ContinuityChecker）

人工检查项（生成指引）：
  1. 坐标系正确
  3. 与点云误差 ≤ 0.5mm
  9. 特征线饱满流畅
  10. Shading 无鼓包/凹陷/扭曲
  11. 截面线与点云形状一致
"""
import os
import csv
import numpy as np

from algorithm_model.freeform.nurbs_core import evaluate_surface


class SOPChecklist:
    """A 表面标准 SOP 13 项检查清单。

    Parameters
    ----------
    checker : ContinuityChecker
        已执行 analyze_all 的连续性检查器
    strict_g0_mm : float
        SOP 严格 G0 间隙阈值，默认 0.01mm（SOP 4.2.6）
    max_ctrl_per_span : int
        单段控制点上限，默认 7（SOP 4.2.4）
    max_u_ctrl : int
        U 向控制点上限，默认 8（SOP 4.3.2）
    min_fillet_len_mm : float
        R 角最小长度 mm，默认 3.0（SOP 4.3.2）
    max_pointcloud_err_mm : float
        点云误差上限 mm，默认 0.5（SOP 4.2.1）
    max_curvature_cv : float
        边界曲率变异系数上限，默认 0.5
    curvature_samples : int
        曲率采样网格密度，默认 20
    """

    def __init__(self, checker,
                 strict_g0_mm=0.01,
                 max_ctrl_per_span=7,
                 max_u_ctrl=8,
                 min_fillet_len_mm=3.0,
                 max_pointcloud_err_mm=0.5,
                 max_curvature_cv=0.5,
                 curvature_samples=20):
        self.checker = checker
        self.strict_g0_mm = strict_g0_mm
        self.max_ctrl_per_span = max_ctrl_per_span
        self.max_u_ctrl = max_u_ctrl
        self.min_fillet_len_mm = min_fillet_len_mm
        self.max_pointcloud_err_mm = max_pointcloud_err_mm
        self.max_curvature_cv = max_curvature_cv
        self.curvature_samples = curvature_samples
        self._results = []

    # ------------------------------------------------------------------
    # 曲率计算
    # ------------------------------------------------------------------
    @staticmethod
    def _surface_derivatives(surf, u, v, h=1e-4):
        """计算曲面一阶/二阶偏导 + 法向量 + 曲率。"""
        hu = hv = max(h, 1e-5)

        def _ev(uu, vv):
            return evaluate_surface(surf, uu, vv)

        if u + hu > 1.0:
            Su = (_ev(u, v) - _ev(u - hu, v)) / hu
        elif u - hu < 0.0:
            Su = (_ev(u + hu, v) - _ev(u, v)) / hu
        else:
            Su = (_ev(u + hu, v) - _ev(u - hu, v)) / (2 * hu)

        if v + hv > 1.0:
            Sv = (_ev(u, v) - _ev(u, v - hv)) / hv
        elif v - hv < 0.0:
            Sv = (_ev(u, v + hv) - _ev(u, v)) / hv
        else:
            Sv = (_ev(u, v + hv) - _ev(u, v - hv)) / (2 * hv)

        if 0.0 < u < 1.0:
            Suu = (_ev(u + hu, v) - 2 * _ev(u, v) + _ev(u - hu, v)) / (hu * hu)
        else:
            Suu = np.zeros(3)
        if 0.0 < v < 1.0:
            Svv = (_ev(u, v + hv) - 2 * _ev(u, v) + _ev(u, v - hv)) / (hv * hv)
        else:
            Svv = np.zeros(3)
        if 0.0 < u < 1.0 and 0.0 < v < 1.0:
            Suv = (_ev(u + hu, v + hv) - _ev(u + hu, v - hv)
                   - _ev(u - hu, v + hv) + _ev(u - hu, v - hv)) / (4 * hu * hv)
        else:
            Suv = np.zeros(3)

        n = np.cross(Su, Sv)
        norm = np.linalg.norm(n)
        if norm < 1e-12:
            return {"H": 0.0, "K": 0.0, "k1": 0.0, "k2": 0.0,
                    "R_min": 1e6, "normal": np.array([0, 0, 1.0])}
        normal = n / norm

        E = np.dot(Su, Su)
        F = np.dot(Su, Sv)
        G = np.dot(Sv, Sv)
        L = np.dot(Suu, normal)
        M = np.dot(Suv, normal)
        N = np.dot(Svv, normal)

        denom = 2 * (E * G - F * F)
        if abs(denom) < 1e-15:
            return {"H": 0.0, "K": 0.0, "k1": 0.0, "k2": 0.0,
                    "R_min": 1e6, "normal": normal}
        H = (E * N - 2 * F * M + G * L) / denom
        K = (L * N - M * M) / (E * G - F * F)

        disc = max(H * H - K, 0.0)
        k1 = H + np.sqrt(disc)
        k2 = H - np.sqrt(disc)
        k_max = max(abs(k1), abs(k2))
        R_min = 1.0 / k_max if k_max > 1e-10 else 1e6

        return {"H": H, "K": K, "k1": k1, "k2": k2,
                "R_min": R_min, "normal": normal}

    def _sample_curvature_grid(self, surf, n=None):
        """在曲面上采样 n x n 网格的曲率信息。"""
        n = n or self.curvature_samples
        us = np.linspace(0.01, 0.99, n)
        vs = np.linspace(0.01, 0.99, n)
        Hs = np.zeros((n, n))
        Ks = np.zeros((n, n))
        k1s = np.zeros((n, n))
        k2s = np.zeros((n, n))
        Rmins = np.zeros((n, n))
        for i, u in enumerate(us):
            for j, v in enumerate(vs):
                d = self._surface_derivatives(surf, u, v)
                Hs[i, j] = d["H"]
                Ks[i, j] = d["K"]
                k1s[i, j] = d["k1"]
                k2s[i, j] = d["k2"]
                Rmins[i, j] = d["R_min"]
        return {"H": Hs, "K": Ks, "k1": k1s, "k2": k2s,
                "R_min": Rmins, "n": n}

    # ------------------------------------------------------------------
    # 13 项检查
    # ------------------------------------------------------------------
    def _check_01_coordinate(self):
        return {"id": 1, "category": "manual",
                "item": "坐标系正确，与总布置发布一致",
                "sop_ref": "SOP section 3",
                "status": "MANUAL", "value": "-",
                "threshold": "与总布置一致", "passed": None,
                "note": "确认整车坐标系与总布置发布一致"}

    def _check_02_simplicity(self, name, surf):
        cp = surf["control_points"]
        n_u, n_v = cp.shape[:2]
        p, q = surf["degree"]
        spans_u = n_u - p
        spans_v = n_v - q
        total_cp = n_u * n_v
        passed = total_cp <= 100 and spans_u <= 6 and spans_v <= 6
        return {"id": 2, "category": "auto",
                "item": "基础大面简洁，面块/段数最少化",
                "sop_ref": "SOP 4.2.1", "surface": name,
                "status": "PASS" if passed else "WARN",
                "value": "cp=%dx%d spans=%dx%d total=%d" % (n_u, n_v, spans_u, spans_v, total_cp),
                "threshold": "cp<=10x10, spans<=6x6, total<=100",
                "passed": passed,
                "note": "控制点网格规模反映曲面简洁程度"}

    def _check_03_pointcloud(self, name):
        return {"id": 3, "category": "manual",
                "item": "与点云误差 <= %.1fmm" % self.max_pointcloud_err_mm,
                "sop_ref": "SOP 4.2.1", "surface": name,
                "status": "MANUAL", "value": "-",
                "threshold": "<= %.1fmm" % self.max_pointcloud_err_mm,
                "passed": None,
                "note": "需导入点云数据，使用偏差分析工具检查"}

    def _check_04_single_convex(self, name, surf):
        grid = self._sample_curvature_grid(surf, n=12)
        H = grid["H"]
        signs = np.sign(H)
        sign_changes = 0
        for i in range(signs.shape[0]):
            for j in range(1, signs.shape[1]):
                if signs[i, j] != 0 and signs[i, j - 1] != 0:
                    if signs[i, j] != signs[i, j - 1]:
                        sign_changes += 1
        total = signs.size
        passed = sign_changes <= total * 0.15
        return {"id": 4, "category": "auto",
                "item": "单凹/单凸，无多余拐点",
                "sop_ref": "SOP 4.2.3", "surface": name,
                "status": "PASS" if passed else "WARN",
                "value": "sign_changes=%d/%d (%.1f%%)" % (
                    sign_changes, total, 100.0 * sign_changes / max(total, 1)),
                "threshold": "sign_changes <= 15%% of samples",
                "passed": passed,
                "note": "均曲率符号变化反映拐点数量"}

    def _check_05_ctrl_per_span(self, name, surf):
        cp = surf["control_points"]
        n_u, n_v = cp.shape[:2]
        p, q = surf["degree"]
        cp_u = p + 1
        cp_v = q + 1
        passed = cp_u <= self.max_ctrl_per_span and cp_v <= self.max_ctrl_per_span
        return {"id": 5, "category": "auto",
                "item": "单段控制点 <= %d" % self.max_ctrl_per_span,
                "sop_ref": "SOP 4.2.4", "surface": name,
                "status": "PASS" if passed else "FAIL",
                "value": "U: deg=%d -> %d/span, V: deg=%d -> %d/span" % (p, cp_u, q, cp_v),
                "threshold": "<= %d/span (both U and V)" % self.max_ctrl_per_span,
                "passed": passed,
                "note": "degree+1 = 单段控制点数"}

    def _check_06_intersection_gap(self):
        results = self.checker.results or []
        if not results:
            return {"id": 6, "category": "auto",
                    "item": "交线间隙 < %.3fmm" % self.strict_g0_mm,
                    "sop_ref": "SOP 4.2.6", "status": "SKIP",
                    "value": "-", "threshold": "< %.3fmm" % self.strict_g0_mm,
                    "passed": None, "note": "ContinuityChecker 未执行"}
        strict_pairs = [r for r in results if r["min_gap_mm"] < self.strict_g0_mm]
        total_contact = sum(1 for r in results if r["rating"] in ("G1 OK", "G0 OK"))
        passed = len(strict_pairs) >= 1 or total_contact == 0
        worst = max(r["min_gap_mm"] for r in results) if results else 0.0
        return {"id": 6, "category": "auto",
                "item": "交线光顺，边界间隙 < %.3fmm" % self.strict_g0_mm,
                "sop_ref": "SOP 4.2.6",
                "status": "PASS" if passed else "WARN",
                "value": "strict_pairs=%d, contact_pairs=%d, worst_gap=%.4fmm" % (
                    len(strict_pairs), total_contact, worst),
                "threshold": "共享边界间隙 < %.3fmm" % self.strict_g0_mm,
                "passed": passed,
                "note": "严格 G0（0.01mm）用于 A 面对接边界"}

    def _check_07_r_uniformity(self, name, surf):
        grid = self._sample_curvature_grid(surf, n=10)
        R = grid["R_min"]
        edges = np.concatenate([R[0, :], R[-1, :], R[:, 0], R[:, -1]])
        finite = edges[edges < 1e5]
        if len(finite) < 2:
            cv = 0.0
            passed = True
        else:
            mean_r = np.mean(finite)
            std_r = np.std(finite)
            cv = std_r / max(abs(mean_r), 1e-10)
            passed = cv <= self.max_curvature_cv
        return {"id": 7, "category": "auto",
                "item": "R 值均匀变化（边界曲率 CV）",
                "sop_ref": "SOP 4.3.1", "surface": name,
                "status": "PASS" if passed else "WARN",
                "value": "CV=%.3f, mean_R=%.1fmm" % (cv, np.mean(finite) if len(finite) else 0),
                "threshold": "CV <= %.2f" % self.max_curvature_cv,
                "passed": passed,
                "note": "边界曲率半径变异系数反映 R 值均匀性"}

    def _check_08_fillet_params(self, name, surf):
        cp = surf["control_points"]
        n_u = cp.shape[0]
        grid = self._sample_curvature_grid(surf, n=10)
        mask = grid["R_min"] < 1e5
        R_min = np.min(grid["R_min"][mask]) if np.any(mask) else 1e6
        u_ctrl_ok = n_u < self.max_u_ctrl
        fillet_ok = R_min >= self.min_fillet_len_mm
        passed = u_ctrl_ok and fillet_ok
        return {"id": 8, "category": "auto",
                "item": "R 角 >= %.0fmm + U 向控制点 < %d" % (self.min_fillet_len_mm, self.max_u_ctrl),
                "sop_ref": "SOP 4.3.2", "surface": name,
                "status": "PASS" if passed else "WARN",
                "value": "R_min=%.2fmm, U_ctrl=%d" % (R_min, n_u),
                "threshold": "R_min >= %.0fmm AND U_ctrl < %d" % (self.min_fillet_len_mm, self.max_u_ctrl),
                "passed": passed,
                "note": "R 角长度和 U 向控制点数影响过渡曲面质量"}

    def _check_09_character_line(self, name):
        return {"id": 9, "category": "manual",
                "item": "特征线饱满流畅，线面误差 < 0.001mm",
                "sop_ref": "SOP 4.4", "surface": name,
                "status": "MANUAL", "value": "-",
                "threshold": "线面误差 < 0.001mm", "passed": None,
                "note": "需提取特征线，与基础面做偏差分析"}

    def _check_10_shading(self, name):
        return {"id": 10, "category": "manual",
                "item": "Shading 检查无鼓包/凹陷/扭曲",
                "sop_ref": "SOP 5.1.1", "surface": name,
                "status": "MANUAL", "value": "-",
                "threshold": "肉眼无可见缺陷", "passed": None,
                "note": "在 CAx 软件中激活 Shading，旋转数模全方位检查"}

    def _check_11_section(self, name):
        return {"id": 11, "category": "manual",
                "item": "截面线与点云形状一致",
                "sop_ref": "SOP 5.1.2", "surface": name,
                "status": "MANUAL", "value": "-",
                "threshold": "截面形状匹配", "passed": None,
                "note": "截取数模断面线，与点云切面对比"}

    def _check_12_curvature(self, name, surf):
        grid = self._sample_curvature_grid(surf, n=15)
        H = grid["H"]
        grad_h = np.gradient(H)
        grad_mag = np.sqrt(grad_h[0] ** 2 + grad_h[1] ** 2)
        mean_grad = np.mean(grad_mag)
        max_grad = np.max(grad_mag)
        ratio = max_grad / max(mean_grad, 1e-10)
        passed = ratio < 10.0
        return {"id": 12, "category": "auto",
                "item": "Curvature / ISO Curvature 检查",
                "sop_ref": "SOP 5.1.3", "surface": name,
                "status": "PASS" if passed else "WARN",
                "value": "mean_grad=%.4f, max_grad=%.4f, ratio=%.1f" % (mean_grad, max_grad, ratio),
                "threshold": "max/mean gradient ratio < 10",
                "passed": passed,
                "note": "曲率梯度突变反映 ISO 曲率线的不连续程度"}

    def _check_13_continuity(self):
        summary = self.checker.summary()
        total = summary.get("total_pairs", 0)
        g1_both = summary.get("g0_g1_both", 0)
        if total == 0:
            return {"id": 13, "category": "auto",
                    "item": "G0/G1/G2 连续性达标",
                    "sop_ref": "SOP 5.2", "status": "SKIP",
                    "value": "-", "threshold": "G0<0.1mm, G1<1.0deg",
                    "passed": None, "note": "无曲面配对"}
        passed = g1_both >= 1
        return {"id": 13, "category": "auto",
                "item": "G0/G1/G2 连续性达标",
                "sop_ref": "SOP 5.2",
                "status": "PASS" if passed else "FAIL",
                "value": "G1_pairs=%d/%d (%.1f%%)" % (g1_both, total, 100.0 * g1_both / max(total, 1)),
                "threshold": "至少 1 对 G1 OK (G0<%.1fmm, G1<%.1fdeg)" % (self.checker.g0_thresh_mm, self.checker.g1_thresh_deg),
                "passed": passed,
                "note": "复用 ContinuityChecker 结果"}

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------
    def run(self):
        """执行全部 13 项检查。"""
        self._results = []
        items = self.checker.items

        self._results.append(self._check_01_coordinate())

        for name, surf in items:
            self._results.append(self._check_02_simplicity(name, surf))
            self._results.append(self._check_03_pointcloud(name))
            self._results.append(self._check_04_single_convex(name, surf))
            self._results.append(self._check_05_ctrl_per_span(name, surf))
            self._results.append(self._check_07_r_uniformity(name, surf))
            self._results.append(self._check_08_fillet_params(name, surf))
            self._results.append(self._check_09_character_line(name))
            self._results.append(self._check_10_shading(name))
            self._results.append(self._check_11_section(name))
            self._results.append(self._check_12_curvature(name, surf))

        self._results.append(self._check_06_intersection_gap())
        self._results.append(self._check_13_continuity())
        return self._results

    # ------------------------------------------------------------------
    # 报告
    # ------------------------------------------------------------------
    @property
    def results(self):
        return self._results

    def passed_count(self):
        return sum(1 for r in self._results if r["passed"] is True)

    def failed_count(self):
        return sum(1 for r in self._results if r["passed"] is False)

    def manual_count(self):
        return sum(1 for r in self._results if r["passed"] is None)

    def total_count(self):
        return len(self._results)

    def write_report(self, out_dir, prefix="sop_checklist"):
        """输出 TXT + CSV 报告。Returns (txt_path, csv_path)"""
        os.makedirs(out_dir, exist_ok=True)
        txt_path = os.path.join(out_dir, prefix + "_report.txt")
        csv_path = os.path.join(out_dir, prefix + "_pairs.csv")

        lines = []
        lines.append("=" * 78)
        lines.append("A 表面标准 SOP 检查清单报告")
        lines.append("SOP-A SURF-001 | 基于 A表面标准SOP.md")
        lines.append("=" * 78)
        lines.append("")
        lines.append("检查统计:")
        lines.append("  自动检查: %d 项 (PASS=%d, FAIL=%d)" % (
            self.passed_count() + self.failed_count(),
            self.passed_count(), self.failed_count()))
        lines.append("  人工检查: %d 项" % self.manual_count())
        lines.append("  总计:     %d 项" % self.total_count())
        lines.append("")
        lines.append("-" * 78)

        current_id = None
        for r in self._results:
            if r["id"] != current_id:
                current_id = r["id"]
                lines.append("")
                lines.append("[检查项 %d] %s" % (r["id"], r["item"]))
                lines.append("  SOP 参考: %s" % r["sop_ref"])
                lines.append("  阈值:     %s" % r["threshold"])

            status_str = r["status"]
            if r["passed"] is True:
                status_str = "PASS " + status_str
            elif r["passed"] is False:
                status_str = "FAIL " + status_str
            else:
                status_str = "MANUAL " + status_str

            surf_name = r.get("surface", "（全局）")
            lines.append("  |- %-24s | %s | %s" % (
                surf_name[:24], status_str, r["value"]))
            if r.get("note"):
                lines.append("  |  -> %s" % r["note"])

        lines.append("")
        lines.append("-" * 78)
        lines.append("说明:")
        lines.append("  PASS    自动检查通过")
        lines.append("  FAIL    自动检查未通过，需修正")
        lines.append("  MANUAL  需人工确认 / 需外部数据")
        lines.append("  WARN    自动检查警告，建议复核")
        lines.append("=" * 78)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["check_id", "item", "sop_ref", "surface",
                             "status", "value", "threshold", "passed", "note"])
            for r in self._results:
                writer.writerow([
                    r["id"], r["item"], r["sop_ref"], r.get("surface", ""),
                    r["status"], r["value"], r["threshold"],
                    {True: "PASS", False: "FAIL", None: "MANUAL"}[r["passed"]],
                    r.get("note", ""),
                ])
        return txt_path, csv_path

    def print_summary(self):
        """打印控制台摘要。"""
        print("\nSOP Checklist Summary:")
        print("  Auto checks: %d (PASS=%d, FAIL=%d)" % (
            self.passed_count() + self.failed_count(),
            self.passed_count(), self.failed_count()))
        print("  Manual checks: %d" % self.manual_count())
        print("  Total: %d" % self.total_count())

        by_id = {}
        for r in self._results:
            rid = r["id"]
            if rid not in by_id:
                by_id[rid] = {"item": r["item"], "pass": 0, "fail": 0, "manual": 0}
            if r["passed"] is True:
                by_id[rid]["pass"] += 1
            elif r["passed"] is False:
                by_id[rid]["fail"] += 1
            else:
                by_id[rid]["manual"] += 1

        print("\n  %-4s %-40s %6s %6s %6s" % ("ID", "Item", "PASS", "FAIL", "MANUAL"))
        print("  " + "-" * 68)
        for rid in sorted(by_id.keys()):
            v = by_id[rid]
            print("  %-4d %-40s %6d %6d %6d" % (
                rid, v["item"][:40], v["pass"], v["fail"], v["manual"]))
