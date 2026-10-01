"""影响证据系统 · 数据收集、统计口径与 RBAC 测试

覆盖：
- 埋点：track 落地 + duration 回填（幂等取最大值）
- 公开汇总：结构完整、90 天上限、非法维度拒绝
- 留言：提交/列表/隐藏剔除/管理员回复
- 引用：提交去重/公开仅已核验/管理员核验
- 权限：游客 401、普通用户 403、管理员 200
- 导出：CSV/JSON 仅管理员，白名单校验
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import (ExternalReference, Message, PageView, SessionLocal,
                          User, init_db)
from app.security import create_access_token, hash_password

client = TestClient(app)

TEST_EMAILS = ["an_user@test.local", "an_admin@test.local"]


def _make_user(db, email, role):
    user = User(email=email, username=email.split("@")[0],
                password_hash=hash_password("pass123456"),
                role=role, is_admin=role == "admin", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def accounts():
    init_db()
    db = SessionLocal()
    try:
        users = {
            "user": _make_user(db, "an_user@test.local", "user"),
            "admin": _make_user(db, "an_admin@test.local", "admin"),
        }
        yield users
        for model in (PageView, Message, ExternalReference):
            db.query(model).delete()
        db.query(User).filter(User.email.in_(TEST_EMAILS)).delete()
        db.commit()
    finally:
        db.close()


def _h(user):
    token = create_access_token({"sub": str(user.id), "email": user.email,
                                 "role": user.role})
    return {"Authorization": f"Bearer {token}"}


# ── 埋点 ─────────────────────────────────────

class TestTrack:
    def test_track_creates_view(self, accounts):
        r = client.post("/api/v1/analytics/track", json={
            "visitor_id": "visitor-test-0001",
            "session_id": "session-test-0001",
            "path": "/designer",
            "referrer": "https://github.com/"})
        assert r.status_code == 200
        assert "id" in r.json()

    def test_duration_backfill_max_only(self, accounts):
        r = client.post("/api/v1/analytics/track", json={
            "visitor_id": "visitor-test-0002",
            "session_id": "session-test-0002",
            "path": "/"})
        view_id = r.json()["id"]
        ok = client.post("/api/v1/analytics/track/duration",
                        json={"view_id": view_id, "duration_seconds": 120})
        assert ok.json()["duration_seconds"] == 120
        # 较小值不得覆盖
        client.post("/api/v1/analytics/track/duration",
                    json={"view_id": view_id, "duration_seconds": 30})
        again = client.post("/api/v1/analytics/track/duration",
                           json={"view_id": view_id, "duration_seconds": 200})
        assert again.json()["duration_seconds"] == 200

    def test_track_requires_fields(self, accounts):
        r = client.post("/api/v1/analytics/track", json={"path": "/"})
        assert r.status_code == 422


# ── 公开汇总 ─────────────────────────────────

class TestPublicSummary:
    def _seed_views(self, n=5):
        db = SessionLocal()
        try:
            for i in range(n):
                db.add(PageView(
                    visitor_id=f"v-{i % 3}",
                    session_id=f"s-{i}",
                    path=["/", "/designer"][i % 2],
                    duration_seconds=60 + i,
                    created_at=datetime.utcnow() - timedelta(hours=i)))
            db.commit()
        finally:
            db.close()

    def test_summary_structure(self, accounts):
        self._seed_views()
        r = client.get("/api/v1/analytics/public-summary",
                      params={"granularity": "day", "days": 7})
        assert r.status_code == 200
        body = r.json()
        for key in ("kpi", "series", "top_pages", "top_platforms"):
            assert key in body
        for key in ("visits", "registrations", "messages", "references"):
            assert key in body["series"]
        # PV/UV 字段齐全
        point = body["series"]["visits"][0]
        assert {"bucket", "pv", "uv"} <= set(point)

    def test_summary_caps_days_at_90(self, accounts):
        r = client.get("/api/v1/analytics/public-summary",
                      params={"granularity": "day", "days": 300})
        assert r.json()["days"] == 90

    def test_invalid_granularity_rejected(self, accounts):
        r = client.get("/api/v1/analytics/public-summary",
                      params={"granularity": "year", "days": 7})
        assert r.status_code == 422


# ── 留言互动 ─────────────────────────────────

class TestMessages:
    def test_create_and_list(self, accounts):
        r = client.post("/api/v1/analytics/messages", json={
            "guest_name": "测试访客",
            "content": "这是一条测试留言"})
        assert r.status_code == 200
        lst = client.get("/api/v1/analytics/messages")
        assert any(m["content"] == "这是一条测试留言"
                  for m in lst.json()["items"])

    def test_hidden_messages_excluded(self, accounts):
        db = SessionLocal()
        try:
            db.add(Message(guest_name="hide-me", content="应被隐藏",
                           is_hidden=True))
            db.add(Message(guest_name="show-me", content="正常显示"))
            db.commit()
        finally:
            db.close()
        items = client.get("/api/v1/analytics/messages").json()["items"]
        contents = [m["content"] for m in items]
        assert "正常显示" in contents
        assert "应被隐藏" not in contents

    def test_guest_cannot_reply(self, accounts):
        db = SessionLocal()
        try:
            m = Message(guest_name="g", content="c")
            db.add(m)
            db.commit()
            mid = m.id
        finally:
            db.close()
        assert client.post(
            f"/api/v1/analytics/messages/{mid}/reply",
            json={"reply": "回复"}).status_code == 401

    def test_user_cannot_reply(self, accounts):
        db = SessionLocal()
        try:
            m = Message(guest_name="g", content="c")
            db.add(m)
            db.commit()
            mid = m.id
        finally:
            db.close()
        r = client.post(f"/api/v1/analytics/messages/{mid}/reply",
                       json={"reply": "回复"}, headers=_h(accounts["user"]))
        assert r.status_code == 403

    def test_admin_reply(self, accounts):
        db = SessionLocal()
        try:
            m = Message(guest_name="g", content="c")
            db.add(m)
            db.commit()
            mid = m.id
        finally:
            db.close()
        r = client.post(f"/api/v1/analytics/messages/{mid}/reply",
                       json={"reply": "官方回复"},
                       headers=_h(accounts["admin"]))
        assert r.status_code == 200


# ── 外部引用 ─────────────────────────────────

class TestReferences:
    def test_submit_dedup(self, accounts):
        payload = {"source_url": "https://x.com/p/1",
                   "source_platform": "X / Twitter"}
        first = client.post("/api/v1/analytics/references", json=payload)
        second = client.post("/api/v1/analytics/references", json=payload)
        assert first.json()["duplicate"] is False
        assert second.json()["duplicate"] is True

    def test_public_only_verified(self, accounts):
        db = SessionLocal()
        try:
            db.add(ExternalReference(source_url="https://a/1",
                                     source_platform="知乎", verified=False))
            db.add(ExternalReference(source_url="https://b/2",
                                     source_platform="CSDN", verified=True))
            db.commit()
        finally:
            db.close()
        urls = [r["source_url"]
                for r in client.get("/api/v1/analytics/references")
                .json()["items"]]
        assert "https://b/2" in urls
        assert "https://a/1" not in urls

    def test_admin_verify_toggle(self, accounts):
        db = SessionLocal()
        try:
            ref = ExternalReference(source_url="https://c/3",
                                    source_platform="B站", verified=False)
            db.add(ref)
            db.commit()
            rid = ref.id
        finally:
            db.close()
        r = client.post(f"/api/v1/analytics/references/{rid}/verify",
                       headers=_h(accounts["admin"]))
        assert r.json()["verified"] is True

    def test_guest_verify_denied(self, accounts):
        assert client.post(
            "/api/v1/analytics/references/1/verify").status_code == 401


# ── 管理员分析端点 RBAC ──────────────────────

class TestAdminEndpoints:
    @pytest.mark.parametrize("path", [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/visits?days=7",
        "/api/v1/analytics/registrations?days=7",
        "/api/v1/analytics/interactions?days=7",
        "/api/v1/analytics/references/all",
    ])
    def test_guest_401(self, accounts, path):
        assert client.get(path).status_code == 401

    @pytest.mark.parametrize("path", [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/visits?days=7",
        "/api/v1/analytics/references/all",
    ])
    def test_user_403(self, accounts, path):
        r = client.get(path, headers=_h(accounts["user"]))
        assert r.status_code == 403

    def test_admin_overview_ok(self, accounts):
        r = client.get("/api/v1/analytics/overview",
                      headers=_h(accounts["admin"]))
        assert r.status_code == 200
        assert {"today", "last_7d", "last_30d"} <= set(r.json())

    def test_visits_series_gap_filled(self, accounts):
        r = client.get("/api/v1/analytics/visits",
                      params={"granularity": "day", "days": 14},
                      headers=_h(accounts["admin"]))
        # 14 天完整序列（含补零）
        assert len(r.json()["series"]) == 15


# ── 数据导出 ─────────────────────────────────

class TestExport:
    def test_guest_export_denied(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "visits", "days": 7})
        assert r.status_code == 401

    def test_admin_csv_export(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "visits", "days": 7, "fmt": "csv"},
                      headers=_h(accounts["admin"]))
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"]
        assert "bucket,pv,uv" in r.text

    def test_admin_json_export(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "messages", "days": 7,
                              "fmt": "json"},
                      headers=_h(accounts["admin"]))
        assert r.status_code == 200
        assert r.json()["dataset"] == "messages"

    def test_invalid_dataset(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "passwords", "days": 7},
                      headers=_h(accounts["admin"]))
        assert r.status_code == 422
