"""可验证的影响证据 · 数据收集与统计分析路由

四大证据域：
  1. 访问证据 PageView   —— PV/UV、日周月趋势、停留时长、页面分布
  2. 注册证据 User       —— 注册量趋势（users.created_at 聚合）
  3. 互动证据 Message    —— 留言量、回复量、回复率
  4. 引用证据 ExternalReference —— 外部引用次数、来源平台分布

权限边界：
  - 公开：埋点上报、公开汇总（最长 90 天聚合值，无原始记录）、
    留言查看/提交、已核验引用查看/提交
  - 管理员（admin/superadmin）：全量明细、自定义区间、回复/核验/隐藏、数据导出

安全要点：
  - 时间维度 granularity 只接受枚举 day/week/month，由后端白名单映射 SQL 表达式，
    前端输入绝不直接拼入 SQL（防注入 + SQLite/PostgreSQL 兼容）
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from ..database import (ExternalReference, Message, PageView, User, get_db)
from ..rate_limit import limit
from ..security import (get_optional_user, require_admin, user_is_admin)

router = APIRouter(prefix="/api/v1/analytics", tags=["影响证据分析"])

# 时间维度白名单（key 同时用于前端参数与 SQL 映射）
_GRANULARITIES = ("day", "week", "month")
_PUBLIC_MAX_DAYS = 90


# ───────────────────────────────────────────────────────────
# 请求 / 响应模型
# ───────────────────────────────────────────────────────────

class TrackIn(BaseModel):
    visitor_id: str = Field(..., min_length=4, max_length=64)
    session_id: str = Field(..., min_length=4, max_length=64)
    path: str = Field(..., min_length=1, max_length=300)
    referrer: Optional[str] = Field(None, max_length=500)


class DurationIn(BaseModel):
    view_id: int
    duration_seconds: int = Field(..., ge=0, le=24 * 3600)


class MessageIn(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    contact: Optional[str] = Field(None, max_length=200)


class ReplyIn(BaseModel):
    reply: str = Field(..., min_length=1, max_length=2000)


class ReferenceIn(BaseModel):
    source_url: str = Field(..., min_length=4, max_length=600)
    source_platform: str = Field(..., min_length=1, max_length=100)
    target_path: Optional[str] = Field(None, max_length=300)
    title: Optional[str] = Field(None, max_length=300)


# ───────────────────────────────────────────────────────────
# 工具：时间分桶（SQLite / PostgreSQL 双兼容）
# ───────────────────────────────────────────────────────────

def _dialect_name(db: Session) -> str:
    return db.bind.dialect.name


def _bucket_expr(column, granularity: str, dialect: str):
    """白名单映射：granularity → 固定 SQL 日期分桶表达式。"""
    if dialect == "sqlite":
        fmt = {"day": "%Y-%m-%d", "week": "%Y-%W", "month": "%Y-%m"}[granularity]
        return func.strftime(fmt, column)
    # postgresql（ISO 周历 IYYY-IW，与 isocalendar 对齐）
    fmt = {"day": "YYYY-MM-DD", "week": "IYYY-IW",
           "month": "YYYY-MM"}[granularity]
    return func.to_char(column, fmt)


def _bucket_labels(start: datetime, end: datetime,
                   granularity: str, dialect: str) -> list[str]:
    """生成完整时间桶标签序列（与 SQL 分桶格式一致），用于补零。"""
    labels: list[str] = []
    cur = start
    seen: set[str] = set()
    while cur <= end:
        if dialect == "sqlite":
            if granularity == "day":
                lab = cur.strftime("%Y-%m-%d")
            elif granularity == "week":
                lab = cur.strftime("%Y-%W")
            else:
                lab = cur.strftime("%Y-%m")
        else:
            if granularity == "day":
                lab = cur.strftime("%Y-%m-%d")
            elif granularity == "week":
                iso = cur.isocalendar()
                lab = f"{iso[0]:04d}-{iso[1]:02d}"
            else:
                lab = cur.strftime("%Y-%m")
        if lab not in seen:
            seen.add(lab)
            labels.append(lab)
        cur += timedelta(days=1 if granularity == "day" else
                         7 if granularity == "week" else 28)
    return labels


def _fill_series(labels: list[str], rows: list[tuple],
                 value_index: int = 1) -> list[dict]:
    """按完整标签序列补零：rows → [{bucket, value}]。"""
    mapping = {r[0]: r[value_index] for r in rows}
    return [{"bucket": b, "value": int(mapping.get(b, 0))} for b in labels]


def _parse_range(granularity: str, days: int,
                 max_days: Optional[int]) -> tuple[datetime, datetime]:
    if granularity not in _GRANULARITIES:
        raise HTTPException(status_code=422,
                            detail="granularity 仅支持 day/week/month")
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail="days 取值范围 1-365")
    if max_days is not None and days > max_days:
        days = max_days
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start, end


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        return xff.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "")[:64]


# ───────────────────────────────────────────────────────────
# 1) 埋点上报（公开）
# ───────────────────────────────────────────────────────────

@router.post("/track")
@limit("120/minute")
def track_view(req: TrackIn, request: Request,
               db: Session = Depends(get_db),
               current: Optional[User] = Depends(get_optional_user)):
    """页面进入埋点：落地一行访问记录，返回 view_id（离页时回填时长）。"""
    view = PageView(
        visitor_id=req.visitor_id,
        session_id=req.session_id,
        path=req.path[:300],
        referrer=(req.referrer or None),
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent", "")[:300],
        user_id=current.id if current else None,
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return {"id": view.id, "created_at": view.created_at.isoformat()}


@router.post("/track/duration")
@limit("120/minute")
def track_duration(req: DurationIn, request: Request,
                   db: Session = Depends(get_db)):
    """页面离开埋点：回填停留时长（取最大值，防 beacon 重复上报覆盖）。"""
    view = db.query(PageView).filter(PageView.id == req.view_id).first()
    if view is None:
        raise HTTPException(status_code=404, detail="访问记录不存在")
    if req.duration_seconds > (view.duration_seconds or 0):
        view.duration_seconds = req.duration_seconds
        db.commit()
    return {"ok": True, "duration_seconds": view.duration_seconds}


# ───────────────────────────────────────────────────────────
# 2) 公开汇总（证据看板聚合数据，最长 90 天，无原始记录）
# ───────────────────────────────────────────────────────────

def _range_counts(db: Session, model, start: datetime,
                  end: datetime) -> int:
    return db.query(func.count(model.id)).filter(
        model.created_at >= start, model.created_at <= end
    ).scalar() or 0


@router.get("/public-summary")
def public_summary(
    granularity: str = Query("day"),
    days: int = Query(30),
    db: Session = Depends(get_db),
):
    """公开证据汇总：总量 KPI + 四类时间序列 + 来源分布。"""
    start, end = _parse_range(granularity, days, _PUBLIC_MAX_DAYS)
    effective_days = min(days, _PUBLIC_MAX_DAYS)
    dialect = _dialect_name(db)
    labels = _bucket_labels(start, end, granularity, dialect)

    # -- 访问序列：PV + UV（UV 单独查询后合并） --
    pv_bucket = _bucket_expr(PageView.created_at, granularity, dialect)
    pv_rows = db.query(
        pv_bucket, func.count(PageView.id)
    ).filter(
        PageView.created_at >= start, PageView.created_at <= end
    ).group_by(pv_bucket).order_by(pv_bucket).all()

    uv_rows = db.query(
        pv_bucket, func.count(distinct(PageView.visitor_id))
    ).filter(
        PageView.created_at >= start, PageView.created_at <= end
    ).group_by(pv_bucket).all()
    uv_map = {r[0]: r[1] for r in uv_rows}
    visits_series = [
        {"bucket": b, "pv": int({r[0]: r[1] for r in pv_rows}.get(b, 0)),
         "uv": int(uv_map.get(b, 0))}
        for b in labels
    ]

    # -- 注册序列 --
    reg_bucket = _bucket_expr(User.created_at, granularity, dialect)
    reg_rows = db.query(
        reg_bucket, func.count(User.id)
    ).filter(
        User.created_at >= start, User.created_at <= end
    ).group_by(reg_bucket).all()
    registrations_series = _fill_series(labels, reg_rows)

    # -- 留言 / 回复序列（仅未隐藏留言计入公开统计；回复按留言创建时间归桶） --
    msg_bucket = _bucket_expr(Message.created_at, granularity, dialect)
    msg_rows = db.query(
        msg_bucket, func.count(Message.id)
    ).filter(
        Message.created_at >= start, Message.created_at <= end,
        Message.is_hidden.is_(False)
    ).group_by(msg_bucket).all()
    reply_rows = db.query(
        msg_bucket, func.count(Message.id)
    ).filter(
        Message.created_at >= start, Message.created_at <= end,
        Message.is_hidden.is_(False), Message.reply.isnot(None)
    ).group_by(msg_bucket).all()
    msg_map = {r[0]: r[1] for r in msg_rows}
    reply_map = {r[0]: r[1] for r in reply_rows}
    messages_series = [
        {"bucket": b, "value": int(msg_map.get(b, 0)),
         "replies": int(reply_map.get(b, 0))}
        for b in labels
    ]

    # -- 引用序列（仅已核验） --
    ref_bucket = _bucket_expr(ExternalReference.created_at, granularity, dialect)
    ref_rows = db.query(
        ref_bucket, func.count(ExternalReference.id)
    ).filter(
        ExternalReference.created_at >= start,
        ExternalReference.created_at <= end,
        ExternalReference.verified.is_(True)
    ).group_by(ref_bucket).all()
    references_series = _fill_series(labels, ref_rows)

    # -- KPI 总量 --
    total_pv = _range_counts(db, PageView, start, end)
    total_uv = db.query(func.count(distinct(PageView.visitor_id))).filter(
        PageView.created_at >= start, PageView.created_at <= end
    ).scalar() or 0
    avg_duration = db.query(func.avg(PageView.duration_seconds)).filter(
        PageView.created_at >= start, PageView.created_at <= end,
        PageView.duration_seconds > 0
    ).scalar()
    total_reg = _range_counts(db, User, start, end)
    total_msg = db.query(func.count(Message.id)).filter(
        Message.created_at >= start, Message.created_at <= end,
        Message.is_hidden.is_(False)
    ).scalar() or 0
    total_replied = db.query(func.count(Message.id)).filter(
        Message.created_at >= start, Message.created_at <= end,
        Message.is_hidden.is_(False), Message.reply.isnot(None)
    ).scalar() or 0
    total_refs = db.query(func.count(ExternalReference.id)).filter(
        ExternalReference.created_at >= start,
        ExternalReference.created_at <= end,
        ExternalReference.verified.is_(True)
    ).scalar() or 0

    # -- 页面 Top / 引用平台 Top --
    top_pages_rows = db.query(
        PageView.path, func.count(PageView.id)
    ).filter(
        PageView.created_at >= start, PageView.created_at <= end
    ).group_by(PageView.path).order_by(
        func.count(PageView.id).desc()
    ).limit(8).all()
    top_platform_rows = db.query(
        ExternalReference.source_platform,
        func.count(ExternalReference.id)
    ).filter(
        ExternalReference.created_at >= start,
        ExternalReference.created_at <= end,
        ExternalReference.verified.is_(True)
    ).group_by(ExternalReference.source_platform).order_by(
        func.count(ExternalReference.id).desc()
    ).limit(8).all()

    return {
        "granularity": granularity,
        "days": effective_days,
        "generated_at": datetime.utcnow().isoformat(),
        "kpi": {
            "total_pv": total_pv,
            "total_uv": total_uv,
            "avg_duration_seconds": round(float(avg_duration or 0), 1),
            "total_registrations": total_reg,
            "total_messages": total_msg,
            "total_replies": total_replied,
            "reply_rate": round(total_replied / total_msg, 3) if total_msg else 0,
            "total_references": total_refs,
        },
        "series": {
            "visits": visits_series,
            "registrations": registrations_series,
            "messages": messages_series,
            "references": references_series,
        },
        "top_pages": [{"path": r[0], "count": r[1]} for r in top_pages_rows],
        "top_platforms": [{"platform": r[0], "count": r[1]}
                         for r in top_platform_rows],
    }


# ───────────────────────────────────────────────────────────
# 3) 留言互动（公开查看/提交；管理员回复/隐藏）
# ───────────────────────────────────────────────────────────

@router.get("/messages")
def list_messages(page: int = Query(1, ge=1),
                  page_size: int = Query(10, ge=1, le=50),
                  db: Session = Depends(get_db)):
    """公开留言列表（不返回被隐藏留言）。"""
    base = db.query(Message).filter(Message.is_hidden.is_(False))
    total = base.count()
    rows = base.order_by(Message.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": m.id,
                "guest_name": m.guest_name,
                "content": m.content,
                "reply": m.reply,
                "replied_at": m.replied_at.isoformat() if m.replied_at else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in rows
        ],
    }


@router.post("/messages")
@limit("5/minute")
def create_message(req: MessageIn, request: Request,
                   db: Session = Depends(get_db),
                   current: Optional[User] = Depends(get_optional_user)):
    """提交留言（登录用户自动署名并关联账号）。"""
    msg = Message(
        user_id=current.id if current else None,
        guest_name=(current.username if current else req.guest_name)[:100],
        content=req.content,
        contact=req.contact,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "created_at": msg.created_at.isoformat()}


@router.post("/messages/{message_id}/reply")
def reply_message(message_id: int, req: ReplyIn,
                  db: Session = Depends(get_db),
                  current: User = Depends(require_admin)):
    """管理员回复留言。"""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="留言不存在")
    msg.reply = req.reply
    msg.replied_by = current.id
    msg.replied_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/messages/{message_id}/hide")
def hide_message(message_id: int,
                 db: Session = Depends(get_db),
                 current: User = Depends(require_admin)):
    """管理员隐藏不当留言（公开列表与统计中剔除）。"""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="留言不存在")
    msg.is_hidden = not msg.is_hidden
    db.commit()
    return {"ok": True, "is_hidden": msg.is_hidden}


# ───────────────────────────────────────────────────────────
# 4) 外部引用（公开查看已核验；提交待核验；管理员核验）
# ───────────────────────────────────────────────────────────

@router.get("/references")
def list_references(limit: int = Query(20, ge=1, le=100),
                    db: Session = Depends(get_db)):
    """已核验外部引用列表。"""
    rows = db.query(ExternalReference).filter(
        ExternalReference.verified.is_(True)
    ).order_by(ExternalReference.created_at.desc()).limit(limit).all()
    return {
        "total": db.query(func.count(ExternalReference.id)).filter(
            ExternalReference.verified.is_(True)).scalar(),
        "items": [_reference_out(r) for r in rows],
    }


@router.post("/references")
@limit("10/minute")
def submit_reference(req: ReferenceIn, request: Request,
                     db: Session = Depends(get_db)):
    """提交外部引用线索（默认未核验，不进入公开列表）。"""
    if not req.source_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="source_url 必须为合法链接")
    exists = db.query(ExternalReference).filter(
        ExternalReference.source_url == req.source_url
    ).first()
    if exists:
        return {"id": exists.id, "duplicate": True}
    ref = ExternalReference(
        source_url=req.source_url,
        source_platform=req.source_platform,
        target_path=req.target_path,
        title=req.title,
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return {"id": ref.id, "duplicate": False}


@router.get("/references/all")
def list_all_references(page: int = Query(1, ge=1),
                        page_size: int = Query(20, ge=1, le=100),
                        verified: Optional[bool] = Query(None),
                        db: Session = Depends(get_db),
                        current: User = Depends(require_admin)):
    """管理员：全部引用（含待核验）。"""
    base = db.query(ExternalReference)
    if verified is not None:
        base = base.filter(ExternalReference.verified.is_(verified))
    total = base.count()
    rows = base.order_by(ExternalReference.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_reference_out(r) for r in rows],
    }


@router.post("/references/{reference_id}/verify")
def verify_reference(reference_id: int,
                     db: Session = Depends(get_db),
                     current: User = Depends(require_admin)):
    """管理员核验外部引用（核验后进入公开证据列表）。"""
    ref = db.query(ExternalReference).filter(
        ExternalReference.id == reference_id
    ).first()
    if ref is None:
        raise HTTPException(status_code=404, detail="引用记录不存在")
    ref.verified = not ref.verified
    if ref.verified:
        ref.verified_by = current.id
        ref.verified_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "verified": ref.verified}


def _reference_out(r: ExternalReference) -> dict:
    return {
        "id": r.id,
        "source_url": r.source_url,
        "source_platform": r.source_platform,
        "target_path": r.target_path,
        "title": r.title,
        "verified": r.verified,
        "verified_at": r.verified_at.isoformat() if r.verified_at else None,
        "created_at": r.created_at.isoformat(),
    }


# ───────────────────────────────────────────────────────────
# 5) 管理员：明细分析端点（全量区间 + 路径/时长分布）
# ───────────────────────────────────────────────────────────

@router.get("/overview")
def admin_overview(db: Session = Depends(get_db),
                   current: User = Depends(require_admin)):
    """管理员 KPI 总览：今日 / 近 7 天 / 近 30 天。"""
    now = datetime.utcnow()
    result = {}
    for label, delta in (("today", timedelta(hours=24)),
                        ("last_7d", timedelta(days=7)),
                        ("last_30d", timedelta(days=30))):
        start = now - delta
        pv = _range_counts(db, PageView, start, now)
        uv = db.query(func.count(distinct(PageView.visitor_id))).filter(
            PageView.created_at >= start, PageView.created_at <= now
        ).scalar() or 0
        reg = _range_counts(db, User, start, now)
        msg = db.query(func.count(Message.id)).filter(
            Message.created_at >= start, Message.created_at <= now,
            Message.is_hidden.is_(False)
        ).scalar() or 0
        refs = db.query(func.count(ExternalReference.id)).filter(
            ExternalReference.created_at >= start,
            ExternalReference.created_at <= now,
            ExternalReference.verified.is_(True)
        ).scalar() or 0
        result[label] = {"pv": pv, "uv": uv, "registrations": reg,
                        "messages": msg, "references": refs}
    result["total_users"] = db.query(func.count(User.id)).scalar()
    result["pending_references"] = db.query(
        func.count(ExternalReference.id)
    ).filter(ExternalReference.verified.is_(False)).scalar()
    result["unreplied_messages"] = db.query(func.count(Message.id)).filter(
        Message.is_hidden.is_(False), Message.reply.is_(None)
    ).scalar()
    return result


@router.get("/visits")
def visits_analysis(granularity: str = Query("day"),
                    days: int = Query(30),
                    db: Session = Depends(get_db),
                    current: User = Depends(require_admin)):
    """管理员：访问明细序列（PV/UV）+ 平均停留时长 + 页面分布。"""
    start, end = _parse_range(granularity, days, None)
    dialect = _dialect_name(db)
    labels = _bucket_labels(start, end, granularity, dialect)

    bucket = _bucket_expr(PageView.created_at, granularity, dialect)
    pv_rows = db.query(
        bucket, func.count(PageView.id)
    ).filter(
        PageView.created_at >= start, PageView.created_at <= end
    ).group_by(bucket).all()
    uv_rows = db.query(
        bucket, func.count(distinct(PageView.visitor_id))
    ).filter(
        PageView.created_at >= start, PageView.created_at <= end
    ).group_by(bucket).all()
    uv_map = {r[0]: r[1] for r in uv_rows}
    pv_map = {r[0]: r[1] for r in pv_rows}
    series = [
        {"bucket": b, "pv": int(pv_map.get(b, 0)),
         "uv": int(uv_map.get(b, 0))}
        for b in labels
    ]

    avg_duration = db.query(func.avg(PageView.duration_seconds)).filter(
        PageView.created_at >= start, PageView.created_at <= end,
        PageView.duration_seconds > 0
    ).scalar()
    page_rows = db.query(
        PageView.path,
        func.count(PageView.id),
        func.count(distinct(PageView.visitor_id)),
        func.avg(PageView.duration_seconds),
    ).filter(
        PageView.created_at >= start, PageView.created_at <= end
    ).group_by(PageView.path).order_by(
        func.count(PageView.id).desc()
    ).limit(20).all()

    return {
        "series": series,
        "avg_duration_seconds": round(float(avg_duration or 0), 1),
        "pages": [
            {"path": r[0], "pv": r[1], "uv": r[2],
             "avg_duration": round(float(r[3] or 0), 1)}
            for r in page_rows
        ],
    }


@router.get("/registrations")
def registrations_analysis(granularity: str = Query("day"),
                          days: int = Query(30),
                          db: Session = Depends(get_db),
                          current: User = Depends(require_admin)):
    """管理员：注册量趋势 + 累计注册。"""
    start, end = _parse_range(granularity, days, None)
    dialect = _dialect_name(db)
    labels = _bucket_labels(start, end, granularity, dialect)
    bucket = _bucket_expr(User.created_at, granularity, dialect)
    rows = db.query(
        bucket, func.count(User.id)
    ).filter(
        User.created_at >= start, User.created_at <= end
    ).group_by(bucket).all()
    return {
        "series": _fill_series(labels, rows),
        "total_users": db.query(func.count(User.id)).scalar(),
    }


@router.get("/interactions")
def interactions_analysis(granularity: str = Query("day"),
                          days: int = Query(30),
                          db: Session = Depends(get_db),
                          current: User = Depends(require_admin)):
    """管理员：留言/回复序列 + 回复率。"""
    start, end = _parse_range(granularity, days, None)
    dialect = _dialect_name(db)
    labels = _bucket_labels(start, end, granularity, dialect)
    bucket = _bucket_expr(Message.created_at, granularity, dialect)

    msg_rows = db.query(
        bucket, func.count(Message.id)
    ).filter(
        Message.created_at >= start, Message.created_at <= end,
        Message.is_hidden.is_(False)
    ).group_by(bucket).all()
    reply_rows = db.query(
        bucket, func.count(Message.id)
    ).filter(
        Message.created_at >= start, Message.created_at <= end,
        Message.is_hidden.is_(False), Message.reply.isnot(None)
    ).group_by(bucket).all()
    reply_map = {r[0]: r[1] for r in reply_rows}
    msg_map = {r[0]: r[1] for r in msg_rows}
    series = [
        {"bucket": b, "messages": int(msg_map.get(b, 0)),
         "replies": int(reply_map.get(b, 0))}
        for b in labels
    ]
    total_msg = sum(v["messages"] for v in series)
    total_reply = sum(v["replies"] for v in series)
    return {
        "series": series,
        "reply_rate": round(total_reply / total_msg, 3) if total_msg else 0,
    }


# ───────────────────────────────────────────────────────────
# 6) 数据导出（管理员；CSV / JSON）
# ───────────────────────────────────────────────────────────

_DATASETS = ("visits", "registrations", "messages", "references")


@router.get("/export")
def export_data(dataset: str = Query(...),
                granularity: str = Query("day"),
                days: int = Query(30),
                fmt: str = Query("csv"),
                db: Session = Depends(get_db),
                current: User = Depends(require_admin)):
    """导出证据数据：dataset 白名单 + CSV/JSON 两种格式。"""
    if dataset not in _DATASETS:
        raise HTTPException(status_code=422,
                            detail=f"dataset 仅支持 {_DATASETS}")
    if fmt not in ("csv", "json"):
        raise HTTPException(status_code=422, detail="fmt 仅支持 csv/json")

    start, end = _parse_range(granularity, days, None)
    dialect = _dialect_name(db)
    labels = _bucket_labels(start, end, granularity, dialect)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if dataset == "visits":
        data = visits_analysis(granularity=granularity, days=days,
                               db=db, current=current)
        rows = [{"bucket": x["bucket"], "pv": x["pv"], "uv": x["uv"]}
                for x in data["series"]]
        headers = ["bucket", "pv", "uv"]
    elif dataset == "registrations":
        data = registrations_analysis(granularity=granularity, days=days,
                                      db=db, current=current)
        rows = data["series"]
        headers = ["bucket", "value"]
    elif dataset == "messages":
        msgs = db.query(Message).filter(
            Message.created_at >= start, Message.created_at <= end
        ).order_by(Message.created_at).all()
        rows = [
            {"id": m.id, "guest_name": m.guest_name, "content": m.content,
             "reply": m.reply or "", "is_hidden": int(m.is_hidden),
             "created_at": m.created_at.isoformat()}
            for m in msgs
        ]
        headers = ["id", "guest_name", "content", "reply",
                   "is_hidden", "created_at"]
    else:
        refs = db.query(ExternalReference).filter(
            ExternalReference.created_at >= start,
            ExternalReference.created_at <= end
        ).order_by(ExternalReference.created_at).all()
        rows = [
            {"id": r.id, "source_platform": r.source_platform,
             "source_url": r.source_url, "title": r.title or "",
             "verified": int(r.verified),
             "created_at": r.created_at.isoformat()}
            for r in refs
        ]
        headers = ["id", "source_platform", "source_url", "title",
                   "verified", "created_at"]

    if fmt == "json":
        return Response(
            content=json.dumps(
                {"dataset": dataset, "exported_at": stamp, "rows": rows},
                ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition":
                     f'attachment; filename="evidence_{dataset}_{stamp}.json"'},
        )

    # CSV（utf-8-sig 保证 Excel 中文不乱码）
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":
                 f'attachment; filename="evidence_{dataset}_{stamp}.csv"'},
    )
