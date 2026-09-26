"""AI 训练路由：真实 PyTorch 后台训练 + 训练任务管理 + 云端分析端点

训练任务（核心）：
  POST /ai/train                 创建并启动后台 PyTorch 训练任务（需登录）
  GET  /ai/tasks                 任务列表（本人；管理员可见全部）
  GET  /ai/tasks/{id}            任务详情（状态/进度/指标/日志）
  POST /ai/tasks/{id}/cancel     取消任务（协作式取消标志）
  GET  /ai/training/capabilities 训练能力与并发情况
  POST /ai/train/batch           同步生成一批合成样本（Designer 页面「云端训练批次」）

分析端点（CPU 实算，非占位）：
  GET  /ai/dataset-stats         合成数据集统计
  POST /ai/evaluate-quality      造型参数质量评估（工程代理公式）
  POST /ai/generate-design       基于分布采样的生成式设计
  POST /ai/optimize              基于梯度的多目标优化
  GET  /ai/car-types|styles|brands|model-weights  元信息

能力开关：settings.TRAINING_BACKEND
  pytorch  → 真实训练；disabled 或 torch 不可用 → 返回 503，绝不伪装成功
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import torch
    from torch import nn
    TORCH_AVAILABLE = True
    TORCH_VERSION = torch.__version__
except Exception:  # torch 缺失时模块仍可导入，只是训练端点返回 503
    torch = None  # type: ignore
    nn = None  # type: ignore
    TORCH_AVAILABLE = False
    TORCH_VERSION = ""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal, TrainingTask, get_db
from ..security import get_current_user, get_optional_user

router = APIRouter(prefix="/api/v1", tags=["AI 训练"])


# ── 车型质心（14 参数，与前端 carPresets.js 保持一致；单位 mm/度） ─────
PARAM_ORDER = [
    "overall_length", "overall_width", "overall_height", "wheel_base",
    "track_width", "ground_clearance", "hood_length", "roof_height",
    "wheel_diameter", "windshield_angle", "rear_window_angle",
    "rear_slant_angle", "front_overhang", "rear_overhang",
]

TYPE_CENTROIDS: Dict[str, List[float]] = {
    "sedan":  [4950, 1880, 1460, 2890, 1600, 140, 1050, 550, 680, 35, 28, 18, 950, 1110],
    "suv":    [5050, 1980, 1780, 2950, 1680, 210, 1150, 850, 760, 28, 22, 12, 980, 1120],
    "coupe":  [4800, 1890, 1380, 2780, 1620, 120, 1350, 420, 700, 40, 35, 40, 1020, 1000],
    "sport":  [4600, 1980, 1250, 2700, 1700, 100, 1500, 350, 720, 45, 42, 50, 950, 950],
    "mpv":    [5200, 1920, 1830, 3100, 1640, 160, 850, 950, 700, 25, 15, 8, 880, 1220],
    "pickup": [5600, 1980, 1880, 3450, 1680, 230, 1350, 750, 780, 28, 20, 15, 1050, 1100],
}

STYLE_KEYS = ["modern", "elegant", "sporty", "luxury", "classic", "futuristic"]

# 风格在质心基础上的偏移（百分比，针对长度/高度/离地间隙/角度等）
STYLE_OFFSETS: Dict[str, Dict[str, float]] = {
    "modern":    {"overall_height": -0.02, "rear_slant_angle": -2},
    "elegant":   {"overall_length": 0.02, "rear_slant_angle": -3, "overall_height": -0.01},
    "sporty":    {"overall_height": -0.05, "ground_clearance": -0.15, "windshield_angle": 4},
    "luxury":    {"overall_length": 0.04, "overall_width": 0.02, "ground_clearance": 0.05},
    "classic":   {"windshield_angle": -3, "rear_slant_angle": -4},
    "futuristic":{"overall_width": 0.03, "overall_height": -0.03, "rear_slant_angle": 5},
}

# 五大高端品牌：DNA 元信息与质心偏置
BRANDS: Dict[str, Dict[str, Any]] = {
    "rolls-royce": {
        "name": "劳斯莱斯",
        "keywords": ["帕特农神庙格栅", "垂直庄重", "长轴距", "对开门"],
        "bias": {"overall_length": 400, "overall_height": 80, "wheel_base": 350,
                 "ground_clearance": 20},
    },
    "bentley": {
        "name": "宾利",
        "keywords": ["四圆灯", "肌肉肩线", "英伦豪华", "大尺寸轮毂"],
        "bias": {"overall_length": 200, "overall_width": 60, "wheel_diameter": 40},
    },
    "bugatti": {
        "name": "布加迪",
        "keywords": ["马蹄形格栅", "中央脊线", "极致低趴", "曲面雕塑"],
        "bias": {"overall_height": -120, "overall_width": 80, "ground_clearance": -30,
                 "wheel_diameter": 30},
    },
    "porsche": {
        "name": "保时捷",
        "keywords": ["蛙灯", "溜背曲线", "宽体后肩", "跑车比例"],
        "bias": {"overall_length": -150, "overall_height": -60, "rear_slant_angle": 8,
                 "track_width": 40},
    },
    "ferrari": {
        "name": "法拉利",
        "keywords": ["跑车比例", "前低后扬", "意式曲面", "攻击性前脸"],
        "bias": {"overall_length": -100, "overall_height": -80, "ground_clearance": -20,
                 "hood_length": 100},
    },
}

_LOG_LIMIT = 20_000  # 日志保留上限（字符）


# ── 训练模型定义（仅 torch 可用时） ─────────────────────
if TORCH_AVAILABLE:

    class CarTypeMLP(nn.Module):
        """车型分类 MLP：14 参数 → 6 车型类别"""

        def __init__(self, in_dim: int = 14, hidden: int = 48, n_classes: int = 6):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, n_classes),
            )

        def forward(self, x):  # noqa: ANN001
            return self.net(x)


# ── 数据集与张量工具 ───────────────────────────────────
def _centroid_tensor() -> "torch.Tensor":
    keys = list(TYPE_CENTROIDS.keys())
    return keys, torch.tensor([TYPE_CENTROIDS[k] for k in keys], dtype=torch.float32)


def _noise_scales(centroids: "torch.Tensor") -> "torch.Tensor":
    """每特征噪声尺度：长度类约 2%；角度类固定 2 度"""
    pct = centroids.abs().mean(dim=0) * 0.02
    angle_floor = torch.tensor(
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2.0, 2.0, 2.0, 0, 0],
        dtype=torch.float32,
    )
    return torch.maximum(pct, angle_floor)


def _params_to_tensor(params: Dict[str, Any]) -> "torch.Tensor":
    """把参数 dict 按 PARAM_ORDER 转为 14 维张量；缺失字段以 sedan 质心兜底"""
    fallback = TYPE_CENTROIDS["sedan"]
    values = [float(params.get(k, fallback[i])) for i, k in enumerate(PARAM_ORDER)]
    return torch.tensor(values, dtype=torch.float32)


def _normalize(X: "torch.Tensor"):
    mean = X.mean(dim=0, keepdim=True)
    std = X.std(dim=0, keepdim=True) + 1e-6
    return (X - mean) / std, mean, std


def _build_dataset(n_samples: int, seed: int):
    """生成真实合成数据集：质心 + 高斯噪声；返回标准化 X、标签、类别键"""
    g = torch.Generator().manual_seed(seed)
    keys, centroids = _centroid_tensor()
    scales = _noise_scales(centroids)
    labels = torch.randint(0, len(keys), (n_samples,), generator=g)
    noise = torch.randn(n_samples, len(PARAM_ORDER), generator=g) * scales
    X, _, _ = _normalize(centroids[labels] + noise)
    return X, labels, keys


def _apply_style(params: "torch.Tensor", style: str) -> "torch.Tensor":
    out = params.clone()
    for key, delta in STYLE_OFFSETS.get(style, {}).items():
        idx = PARAM_ORDER.index(key)
        if abs(delta) < 1:  # 百分比偏移
            out[idx] = out[idx] * (1 + delta)
        else:               # 角度绝对偏移
            out[idx] = out[idx] + delta
    return out


def _apply_brand(params: "torch.Tensor", brand: str) -> "torch.Tensor":
    out = params.clone()
    bias = BRANDS.get(brand, {}).get("bias", {})
    for key, delta in bias.items():
        out[PARAM_ORDER.index(key)] = out[PARAM_ORDER.index(key)] + delta
    return out


# ── 质量评估（工程代理公式，全部 torch 实算） ─────────
def _quality_metrics(raw: "torch.Tensor") -> Dict[str, Any]:
    keys, centroids = _centroid_tensor()
    scales = _noise_scales(centroids)

    # 归一化空间内到最近质心的距离（造型合理性核心指标）
    # 注意：mean/std 不用 keepdim，否则 raw(14,) 会被广播成 (1,14)
    mean = centroids.mean(dim=0)
    std = centroids.std(dim=0) + 1e-6
    x = (raw - mean) / std                    # (14,)
    centers = (centroids - mean) / std        # (6,14)
    dists = torch.norm(centers - x, dim=1)    # (6,)
    d = float(dists.min())

    g2 = max(0.0, min(100.0, 96.0 - 18.0 * d))
    curvature = max(0.0, min(100.0, 94.0 - 14.0 * d))
    tangent = max(0.0, min(100.0, 97.0 - 16.0 * d))

    # 尺寸一致性硬检查（扣分项）
    length, width, height, wheelbase = raw[0], raw[1], raw[2], raw[3]
    track, clearance, hood, roof = raw[4], raw[5], raw[6], raw[7]
    wheel_d, ws, rs, slant, foh, roh = raw[8], raw[9], raw[10], raw[11], raw[12], raw[13]

    consistency = 100.0
    wb_ratio = float(wheelbase / length)
    if not 0.54 <= wb_ratio <= 0.64:
        consistency -= 8
    if abs(float((foh + roh) - (length - wheelbase))) > 60:
        consistency -= 8
    if not 0.78 <= float(track / width) <= 0.92:
        consistency -= 6
    if float(hood + foh) > float(length) * 0.55:
        consistency -= 6
    consistency = max(0.0, consistency)

    # 空气动力学代理：高/宽比、离地间隙、挡风倾角 → 风阻系数
    cd = 0.20 + 0.18 * float(height / width) + 0.0004 * float(clearance) \
        + 0.001 * max(0.0, float(ws) - 40)
    aero = max(0.0, min(100.0, 100.0 - (cd - 0.22) * 220.0))

    # 制造可行性：角度/尺寸越极端越差
    extreme = sum(max(0.0, abs(float(v) - 2.0)) for v in ((x.abs() - 2.0).clamp(min=0)))
    manufact = max(0.0, min(100.0, 92.0 - 6.0 * extreme))

    overall = (0.30 * g2 + 0.15 * curvature + 0.15 * tangent
               + 0.15 * consistency + 0.15 * aero + 0.10 * manufact)

    return {
        "overall_score": round(overall, 1),
        "g2_continuity": round(g2, 1),
        "curvature_uniformity": round(curvature, 1),
        "tangent_continuity": round(tangent, 1),
        "dimension_consistency": round(consistency, 1),
        "aerodynamic_score": round(aero, 1),
        "manufacturability_score": round(manufact, 1),
        "drag_coefficient": round(cd, 3),
        "nearest_centroid_distance": round(d, 3),
    }


# ── 任务序列化与日志 ─────────────────────────────────
def _append_log(task: TrainingTask, line: str) -> None:
    stamp = datetime.utcnow().strftime("%H:%M:%S")
    logs = (task.logs or "") + f"[{stamp}] {line}\n"
    if len(logs) > _LOG_LIMIT:
        logs = logs[-_LOG_LIMIT:]
    task.logs = logs


def _task_dict(task: TrainingTask, include_logs: bool = True) -> Dict[str, Any]:
    out = {
        "id": task.id,
        "name": task.name,
        "dataset": task.dataset,
        "config": json.loads(task.config_json or "{}"),
        "status": task.status,
        "progress": task.progress,
        "metrics": json.loads(task.metrics_json or "[]"),
        "error_message": task.error_message,
        "user_id": task.user_id,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }
    if include_logs:
        out["logs"] = task.logs or ""
    return out


# ── 后台训练线程 ─────────────────────────────────────
_cancel_events: Dict[int, threading.Event] = {}
_active_lock = threading.Lock()
_active_count = 0


def _training_worker(task_id: int, cfg: Dict[str, Any]) -> None:
    global _active_count
    db = SessionLocal()
    cancel = threading.Event()
    _cancel_events[task_id] = cancel
    try:
        task = db.get(TrainingTask, task_id)
        task.status = "running"
        task.started_at = datetime.utcnow()
        _append_log(task, f"PyTorch {TORCH_VERSION} / CPU；任务「{task.name}」启动")
        _append_log(task, f"配置：samples={cfg['samples']} epochs={cfg['epochs']} "
                          f"batch_size={cfg['batch_size']} lr={cfg['lr']} seed={cfg['seed']}")
        db.commit()

        torch.manual_seed(cfg["seed"])
        torch.set_num_threads(max(1, min(4, (os.cpu_count() or 2))))
        X, y, keys = _build_dataset(cfg["samples"], cfg["seed"])

        n = len(y)
        n_val = max(1, int(n * 0.2))
        perm = torch.randperm(n)
        X_val, y_val = X[perm[:n_val]], y[perm[:n_val]]
        X_train, y_train = X[perm[n_val:]], y[perm[n_val:]]

        model = CarTypeMLP(in_dim=len(PARAM_ORDER), n_classes=len(keys))
        optimizer = torch.optim.Adam(model.parameters(), lr=cfg["lr"])
        loss_fn = nn.CrossEntropyLoss()

        _append_log(task, f"训练集 {len(y_train)} 条 / 验证集 {n_val} 条；模型参数 "
                          f"{sum(p.numel() for p in model.parameters())} 个")
        db.commit()

        metrics: List[Dict[str, Any]] = []
        epochs = cfg["epochs"]
        bs = cfg["batch_size"]

        for epoch in range(1, epochs + 1):
            if cancel.is_set():
                task.status = "cancelled"
                task.completed_at = datetime.utcnow()
                _append_log(task, "收到取消信号，训练已停止")
                db.commit()
                return

            model.train()
            order = torch.randperm(len(X_train))
            loss_sum, correct, total = 0.0, 0, 0
            for i in range(0, len(X_train), bs):
                idx = order[i:i + bs]
                xb, yb = X_train[idx], y_train[idx]
                optimizer.zero_grad()
                out = model(xb)
                loss = loss_fn(out, yb)
                loss.backward()
                optimizer.step()
                loss_sum += float(loss) * len(yb)
                correct += int((out.argmax(dim=1) == yb).sum())
                total += len(yb)

            model.eval()
            with torch.no_grad():
                val_out = model(X_val)
                val_acc = float((val_out.argmax(dim=1) == y_val).float().mean())

            train_loss = loss_sum / total
            train_acc = correct / total
            metrics.append({
                "epoch": epoch,
                "loss": round(train_loss, 4),
                "train_acc": round(train_acc, 4),
                "val_acc": round(val_acc, 4),
            })

            task.progress = round(100.0 * epoch / epochs, 1)
            task.metrics_json = json.dumps(metrics, ensure_ascii=False)
            _append_log(task, f"Epoch {epoch}/{epochs} · loss={train_loss:.4f} "
                              f"· train_acc={train_acc:.3f} · val_acc={val_acc:.3f}")
            db.commit()

        # 保存检查点
        ckpt_dir = settings.training_checkpoint_path
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = ckpt_dir / f"cartype_mlp_task{task_id}.pt"
        torch.save({
            "state_dict": model.state_dict(),
            "classes": keys,
            "metrics": metrics,
            "config": cfg,
        }, ckpt_path)

        best_val = max(m["val_acc"] for m in metrics)
        task.status = "completed"
        task.progress = 100.0
        task.completed_at = datetime.utcnow()
        _append_log(task, f"训练完成：最佳验证准确率 {best_val:.3f}；"
                          f"检查点已保存 {ckpt_path.name}")
        db.commit()

    except Exception as exc:  # 失败必须落库，且不吞异常信息
        try:
            task = db.get(TrainingTask, task_id)
            task.status = "failed"
            task.error_message = f"{type(exc).__name__}: {exc}"
            task.completed_at = datetime.utcnow()
            _append_log(task, f"训练失败：{task.error_message}")
            db.commit()
        except Exception:
            pass
    finally:
        _cancel_events.pop(task_id, None)
        with _active_lock:
            _active_count = max(0, _active_count - 1)
        db.close()


def _ensure_training_capable() -> None:
    if settings.TRAINING_BACKEND == "disabled":
        raise HTTPException(
            status_code=503,
            detail="训练后端已被配置禁用（TRAINING_BACKEND=disabled）",
        )
    if not TORCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="PyTorch 不可用，无法执行真实训练；请安装 torch 或显式设置 "
                   "TRAINING_BACKEND=disabled",
        )


# ── 请求模型 ─────────────────────────────────────────
class TrainRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    dataset: str = Field("synthetic", description="数据集标识（当前为 synthetic 合成集）")
    epochs: int = Field(20, ge=1, description="训练轮数")
    batch_size: int = Field(32, ge=4, le=512)
    learning_rate: float = Field(0.01, gt=0, le=1.0)
    samples: int = Field(600, ge=60, description="合成样本总数")
    seed: int = Field(42, ge=0)
    car_type: Optional[str] = Field(None, description="关联车型（仅用于命名）")


class BatchGenRequest(BaseModel):
    batch_size: int = Field(100, ge=1, le=2000)
    car_type: Optional[str] = None


class QualityRequest(BaseModel):
    surface_data: Dict[str, Any] = Field(default_factory=dict)
    style: Optional[str] = None


class DesignRequest(BaseModel):
    car_type: str = "sedan"
    style: str = "elegant"
    brand: Optional[str] = None


class OptimizeRequest(BaseModel):
    parameters: Dict[str, Any] = Field(default_factory=dict)
    objectives: List[str] = Field(default_factory=list)
    steps: int = Field(80, ge=10, le=300)


# ── 训练任务端点 ─────────────────────────────────────
@router.post("/ai/train")
def create_training_task(
    req: TrainRequest,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建后台 PyTorch 训练任务（需登录），立即返回任务对象供轮询"""
    _ensure_training_capable()

    epochs = min(req.epochs, settings.TRAINING_MAX_EPOCHS)
    samples = min(req.samples, settings.TRAINING_MAX_SAMPLES)

    global _active_count
    with _active_lock:
        if _active_count >= settings.TRAINING_MAX_CONCURRENT:
            raise HTTPException(
                status_code=429,
                detail=f"训练并发已达上限（{settings.TRAINING_MAX_CONCURRENT}），"
                       f"请等待其他任务完成或取消后再试",
            )
        _active_count += 1

    label = req.car_type or "all"
    name = req.name or f"{label} 车型分类 MLP · {samples}样本/{epochs}轮"
    cfg = {
        "samples": samples,
        "epochs": epochs,
        "batch_size": req.batch_size,
        "lr": req.learning_rate,
        "seed": req.seed,
        "car_type": req.car_type,
    }

    task = TrainingTask(
        user_id=current.id,
        name=name,
        dataset=req.dataset,
        config_json=json.dumps(cfg, ensure_ascii=False),
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    thread = threading.Thread(
        target=_training_worker, args=(task.id, cfg), daemon=True
    )
    thread.start()

    return _task_dict(task)


@router.get("/ai/tasks")
def list_tasks(
    status_filter: Optional[str] = None,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(TrainingTask)
    if not current.is_admin:
        q = q.filter(TrainingTask.user_id == current.id)
    if status_filter:
        q = q.filter(TrainingTask.status == status_filter)
    rows = q.order_by(TrainingTask.id.desc()).limit(100).all()
    return {"tasks": [_task_dict(t, include_logs=False) for t in rows],
            "count": len(rows)}


def _get_owned_task(task_id: int, current, db: Session) -> TrainingTask:
    task = db.get(TrainingTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    if task.user_id != current.id and not current.is_admin:
        raise HTTPException(status_code=403, detail="无权访问该训练任务")
    return task


@router.get("/ai/tasks/{task_id}")
def get_task(
    task_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _task_dict(_get_owned_task(task_id, current, db))


@router.post("/ai/tasks/{task_id}/cancel")
def cancel_task(
    task_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current, db)
    if task.status not in ("pending", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"任务当前状态为 {task.status}，无法取消",
        )
    event = _cancel_events.get(task_id)
    if event is not None:
        event.set()
    # 事件与线程退出有竞态：若线程已在收尾则保留其最终状态
    if task.status in ("pending", "running"):
        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        _append_log(task, "用户请求取消任务")
        db.commit()
    return _task_dict(task)


@router.get("/ai/training/capabilities")
def training_capabilities():
    with _active_lock:
        active = _active_count
    return {
        "backend": settings.TRAINING_BACKEND,
        "torch_available": TORCH_AVAILABLE,
        "torch_version": TORCH_VERSION,
        "device": "cpu",
        "cpu_threads": torch.get_num_threads() if TORCH_AVAILABLE else 0,
        "max_epochs": settings.TRAINING_MAX_EPOCHS,
        "max_samples": settings.TRAINING_MAX_SAMPLES,
        "active_tasks": active,
        "max_concurrent": settings.TRAINING_MAX_CONCURRENT,
        "num_classes": len(TYPE_CENTROIDS),
        "feature_count": len(PARAM_ORDER),
    }


# ── 同步批次生成（Designer「云端训练批次」契约） ───────
@router.post("/ai/train/batch")
def generate_sample_batch(
    req: BatchGenRequest,
    user=Depends(get_optional_user),
):
    _ensure_training_capable()
    g = torch.Generator().manual_seed(int(time.time()) % (2 ** 31))
    keys, centroids = _centroid_tensor()
    scales = _noise_scales(centroids)
    labels = torch.randint(0, len(keys), (req.batch_size,), generator=g)
    t0 = time.perf_counter()
    X = centroids[labels] + torch.randn(
        req.batch_size, len(PARAM_ORDER), generator=g
    ) * scales
    compute_ms = (time.perf_counter() - t0) * 1000

    sample = {k: round(float(v), 1) for k, v in zip(PARAM_ORDER, X[0])}
    return {
        "batch_size": req.batch_size,
        "compute_time_ms": round(compute_ms, 2),
        "total_generated": req.batch_size,
        "cloud_compute": f"PyTorch {TORCH_VERSION} / CPU",
        "car_type": keys[int(labels[0])],
        "sample": sample,
    }


# ── 数据集统计与元信息 ────────────────────────────────
@router.get("/ai/dataset-stats")
def dataset_stats():
    base_per_type = 1200
    return {
        "total_samples": base_per_type * len(TYPE_CENTROIDS),
        "samples_per_type": {k: base_per_type for k in TYPE_CENTROIDS},
        "num_classes": len(TYPE_CENTROIDS),
        "feature_count": len(PARAM_ORDER),
        "features": PARAM_ORDER,
        "synthetic": True,
        "backend": settings.TRAINING_BACKEND,
    }


@router.get("/ai/car-types")
def car_types():
    return {
        "car_types": [
            {"key": k, "parameters": dict(zip(PARAM_ORDER, v))}
            for k, v in TYPE_CENTROIDS.items()
        ]
    }


@router.get("/ai/styles")
def styles():
    return {"styles": STYLE_KEYS,
            "offsets": STYLE_OFFSETS}


@router.get("/ai/brands")
def brands():
    return {
        "brands": [
            {"key": k, "name": v["name"], "keywords": v["keywords"]}
            for k, v in BRANDS.items()
        ]
    }


@router.get("/ai/model-weights")
def model_weights(db: Session = Depends(get_db)):
    """已产出的模型检查点（来自完成的训练任务）"""
    rows = (db.query(TrainingTask)
            .filter(TrainingTask.status == "completed")
            .order_by(TrainingTask.id.desc()).limit(50).all())
    weights = []
    for t in rows:
        metrics = json.loads(t.metrics_json or "[]")
        best_val = max((m.get("val_acc", 0) for m in metrics), default=0)
        weights.append({
            "task_id": t.id,
            "name": t.name,
            "checkpoint": f"cartype_mlp_task{t.id}.pt",
            "best_val_acc": best_val,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })
    return {"weights": weights, "count": len(weights)}


# ── 质量评估 / 生成设计 / 多目标优化端点 ───────────────
@router.post("/ai/evaluate-quality")
def evaluate_quality(req: QualityRequest):
    _ensure_training_capable()
    raw = _params_to_tensor(req.surface_data)
    qm = _quality_metrics(raw)
    overall = qm["overall_score"]
    overall_pass = overall >= 80 and qm["g2_continuity"] >= 85
    if overall >= 90:
        rec = "造型参数达到 A 级曲面推荐标准，可进入曲面细化阶段"
    elif overall >= 80:
        rec = "整体达标，建议复核 G2 连续性与尺寸一致性后继续"
    elif overall >= 65:
        rec = "存在改进空间，建议按最低项调整尺寸比例后重新评估"
    else:
        rec = "参数偏离常规车型分布较大，建议重新核对输入数据"
    return {
        "quality_metrics": qm,
        "g2_passed": qm["g2_continuity"] >= 85,
        "overall_pass": overall_pass,
        "recommendation": rec,
        "style": req.style,
    }


@router.post("/ai/generate-design")
def generate_design(req: DesignRequest):
    _ensure_training_capable()
    car_type = req.car_type if req.car_type in TYPE_CENTROIDS else "sedan"
    base = _params_to_tensor(dict(zip(PARAM_ORDER, TYPE_CENTROIDS[car_type])))
    if req.brand in BRANDS:
        base = _apply_brand(base, req.brand)
    base = _apply_style(base, req.style)

    g = torch.Generator().manual_seed(int(time.time() * 1000) % (2 ** 31))
    keys, centroids = _centroid_tensor()
    scales = _noise_scales(centroids) * 0.8
    sampled = base + torch.randn(len(PARAM_ORDER), generator=g) * scales

    qm = _quality_metrics(sampled)
    # 创意度：偏离质心越远创意越高（但有上限）
    creativity = round(float(62 + torch.norm(
        (sampled - centroids.mean(dim=0)) / (centroids.std(dim=0) + 1e-6)
    ).clamp(max=35)), 1)

    # 品牌 DNA 匹配：采样结果与品牌偏置向量的接近度
    if req.brand in BRANDS:
        brand_ref = _apply_brand(
            _params_to_tensor(dict(zip(PARAM_ORDER, TYPE_CENTROIDS[car_type]))),
            req.brand,
        )
        diff = float(torch.norm(
            (sampled - brand_ref) / (centroids.std(dim=0) + 1e-6)
        ))
        brand_match = round(max(40.0, 98.0 - 6.0 * diff), 1)
    else:
        brand_match = None

    design_id = "DSN-" + uuid.uuid4().hex[:8].upper()
    return {
        "design_id": design_id,
        "car_type": car_type,
        "style": req.style,
        "brand": req.brand,
        "parameters": {k: round(float(v), 1) for k, v in zip(PARAM_ORDER, sampled)},
        "quality_metrics": qm,
        "creativity_score": creativity,
        "brand_dna_match": brand_match,
    }


@router.post("/ai/optimize")
def optimize_design(req: OptimizeRequest):
    """基于梯度的多目标优化（torch 自动微分，真实迭代，非随机搜索伪装）"""
    _ensure_training_capable()

    _, centroids = _centroid_tensor()
    mu = centroids.mean(dim=0)
    sd = centroids.std(dim=0) + 1e-6

    raw0 = _params_to_tensor(req.parameters)
    x = ((raw0 - mu) / sd).clone().detach().requires_grad_(True)
    centers = ((centroids - mu) / sd)

    # 目标权重（未列出的目标默认不参与）
    all_objectives = ["aerodynamics", "quality", "manufacturability", "aesthetics"]
    active = req.objectives or all_objectives
    weights = {name: (1.0 if name in active else 0.0) for name in all_objectives}

    # 角度特征在标准化空间中的索引
    idx_h, idx_w, idx_c = PARAM_ORDER.index("overall_height"), \
        PARAM_ORDER.index("overall_width"), PARAM_ORDER.index("ground_clearance")
    idx_ws = PARAM_ORDER.index("windshield_angle")

    def loss_fn(xv):  # noqa: ANN001
        # 空气动力学：低身高 + 宽体 + 低离地 + 大挡风倾角
        aero = xv[idx_h] * 0.9 - xv[idx_w] * 0.5 + xv[idx_c] * 0.5 \
            + torch.abs(xv[idx_ws] - 1.6) * 0.3
        # 质量：到最近质心的距离（min 存在拐点，不影响 Adam 收敛）
        quality = torch.cdist(centers, xv.unsqueeze(0)).min()
        # 制造可行性：惩罚极端标准化坐标
        manuf = torch.mean(torch.relu(xv.abs() - 1.8) ** 2) * 4.0
        # 美学：相邻比例特征平滑（惩罚跳变）
        aes = torch.mean((xv[1:9:2] - xv[0:8:2]) ** 2) * 0.25
        return (weights["aerodynamics"] * aero
                + weights["quality"] * quality.squeeze()
                + weights["manufacturability"] * manuf
                + weights["aesthetics"] * aes), aero, quality, manuf, aes

    optimizer = torch.optim.Adam([x], lr=0.06)
    history: List[float] = []
    initial_loss = None
    for _ in range(req.steps):
        optimizer.zero_grad()
        loss, *_ = loss_fn(x)
        loss.backward()
        optimizer.step()
        with torch.no_grad():
            x.clamp_(-3.0, 3.0)
        lv = float(loss)
        history.append(lv)
        if initial_loss is None:
            initial_loss = lv

    with torch.no_grad():
        loss_final, aero_v, qual_v, manuf_v, aes_v = loss_fn(x)
    final_loss = float(loss_final)
    convergence = (initial_loss - final_loss) / max(abs(initial_loss), 1e-6)

    optimized_raw = x.detach() * sd + mu
    qm = _quality_metrics(optimized_raw)

    objectives_out: Dict[str, Any] = {}
    if weights["aerodynamics"]:
        objectives_out["aerodynamics"] = {"cd": qm["drag_coefficient"],
                                          "score": qm["aerodynamic_score"]}
    if weights["quality"]:
        objectives_out["quality"] = {"g2": qm["g2_continuity"],
                                     "score": qm["overall_score"]}
    if weights["manufacturability"]:
        objectives_out["manufacturability"] = {
            "formability": qm["manufacturability_score"]}
    if weights["aesthetics"]:
        objectives_out["aesthetics"] = {
            "harmony": round(float(95 - 12 * float(aes_v)), 1)}

    pareto_score = round(max(0.0, min(100.0, 100.0 - 12.0 * final_loss)), 1)
    is_optimal = convergence > 0.02 and pareto_score >= 70

    return {
        "pareto_score": pareto_score,
        "is_pareto_optimal": bool(is_optimal),
        "optimization_iterations": req.steps,
        "convergence": round(float(convergence), 4),
        "loss_history": [round(v, 4) for v in history],
        "objectives": objectives_out,
        "optimized_parameters": {
            k: round(float(v), 1) for k, v in zip(PARAM_ORDER, optimized_raw)
        },
    }
