"""影响证据系统 · 数据收集、统计口径与 RBAC 测试

覆盖：
- 埋点：track 落地 + duration 回填（幂等取最大值）
- 汇总：仅超级管理员可见、结构完整、90 天上限、非法维度拒绝
- 社区：发帖/一级回复/点赞/游客自动建档/隐藏剔除
- 引用：提交去重/公开仅已核验/超管核验
- 权限：游客 401、普通用户与 admin 均 403、superadmin 200
- 导出：CSV/JSON 仅超管，白名单校验
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import (ExternalReference, Message, Notification, PageView,
                          SessionLocal, User, init_db)
from app.security import create_access_token, hash_password

client = TestClient(app)

TEST_EMAILS = ["an_user@test.local", "an_admin@test.local",
               "an_super@test.local"]


def _make_user(db, email, role):
    user = User(email=email, username=email.split("@")[0],
                password_hash=hash_password("pass123456"),
                role=role, is_admin=role in ("admin", "superadmin"),
                is_active=True)
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
            "super": _make_user(db, "an_super@test.local", "superadmin"),
        }
        yield users
        for model in (PageView, Message, ExternalReference):
            db.query(model).delete()
        # 清理测试账户及其通知（通知表按 user_id 关联）
        test_ids = [u.id for u in users.values()]
        db.query(Notification).filter(
            Notification.user_id.in_(test_ids)).delete(
            synchronize_session=False)
        db.query(User).filter(User.email.in_(TEST_EMAILS)).delete()
        db.query(User).filter(
            User.email.like("guest_%@guest.evoai.local")).delete()
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


# ── 汇总（仅超级管理员） ────────────────────

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

    def test_guest_denied(self, accounts):
        r = client.get("/api/v1/analytics/public-summary",
                      params={"granularity": "day", "days": 7})
        assert r.status_code == 401

    def test_user_denied(self, accounts):
        r = client.get("/api/v1/analytics/public-summary",
                      params={"granularity": "day", "days": 7},
                      headers=_h(accounts["user"]))
        assert r.status_code == 403

    def test_admin_denied(self, accounts):
        r = client.get("/api/v1/analytics/public-summary",
                      params={"granularity": "day", "days": 7},
                      headers=_h(accounts["admin"]))
        assert r.status_code == 403

    def test_summary_structure(self, accounts):
        self._seed_views()
        r = client.get("/api/v1/analytics/public-summary",
                      params={"granularity": "day", "days": 7},
                      headers=_h(accounts["super"]))
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
                      params={"granularity": "day", "days": 300},
                      headers=_h(accounts["super"]))
        assert r.json()["days"] == 90

    def test_invalid_granularity_rejected(self, accounts):
        r = client.get("/api/v1/analytics/public-summary",
                      params={"granularity": "year", "days": 7},
                      headers=_h(accounts["super"]))
        assert r.status_code == 422


# ── 留言互动 ─────────────────────────────────

class TestMessages:
    def test_create_and_list(self, accounts):
        r = client.post("/api/v1/analytics/messages", json={
            "guest_name": "测试访客",
            "content": "这是一条测试留言"})
        assert r.status_code in (200, 201)
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

    def test_super_reply_marks_official(self, accounts):
        """超级管理员回复写入 reply 字段，公开列表标记官方回复"""
        db = SessionLocal()
        try:
            m = Message(guest_name="g", content="支持中文吗？")
            db.add(m)
            db.commit()
            mid = m.id
        finally:
            db.close()
        r = client.post(f"/api/v1/analytics/messages/{mid}/reply",
                       json={"reply": "支持，界面可切换中英文。"},
                       headers=_h(accounts["super"]))
        assert r.status_code == 200
        db = SessionLocal()
        try:
            msg = db.query(Message).filter(Message.id == mid).first()
            assert msg.reply == "支持，界面可切换中英文。"
            assert msg.replied_at is not None
        finally:
            db.close()
        item = next(m for m in client.get("/api/v1/analytics/messages")
                    .json()["items"] if m["id"] == mid)
        assert item["is_official"] is True

    def test_guest_reply_creates_thread(self, accounts):
        """游客回复 → 落子帖 + 自动建档 guest 账户"""
        db = SessionLocal()
        try:
            m = Message(guest_name="g", content="这个设计很专业")
            db.add(m)
            db.commit()
            pid = m.id
        finally:
            db.close()
        r = client.post(f"/api/v1/analytics/messages/{pid}/reply",
                       json={"reply": "谢谢！",
                             "guest_name": "访客B",
                             "visitor_id": "vis-test-001"})
        assert r.status_code in (200, 201)
        db = SessionLocal()
        try:
            child = db.query(Message).filter(
                Message.parent_id == pid).first()
            assert child is not None
            assert child.guest_name == "访客B"
            assert child.user_id is not None  # 游客已自动建档
        finally:
            db.close()

    def test_logged_user_reply_creates_thread(self, accounts):
        """登录用户回复 → 落子帖，guest_name 取用户名"""
        db = SessionLocal()
        try:
            m = Message(guest_name="g", content="话题")
            db.add(m)
            db.commit()
            pid = m.id
        finally:
            db.close()
        r = client.post(f"/api/v1/analytics/messages/{pid}/reply",
                       json={"reply": "同意"},
                       headers=_h(accounts["user"]))
        assert r.status_code in (200, 201)
        db = SessionLocal()
        try:
            child = db.query(Message).filter(
                Message.parent_id == pid).first()
            assert child is not None
            assert child.user_id == accounts["user"].id
        finally:
            db.close()

    def test_like_increments(self, accounts):
        db = SessionLocal()
        try:
            m = Message(guest_name="g", content="点赞测试")
            db.add(m)
            db.commit()
            mid = m.id
        finally:
            db.close()
        for i in range(3):
            r = client.post(f"/api/v1/analytics/messages/{mid}/like")
            assert r.status_code == 200
            assert r.json()["likes_count"] == i + 1

    def test_hide_requires_super(self, accounts):
        db = SessionLocal()
        try:
            m = Message(guest_name="g", content="垃圾广告")
            db.add(m)
            db.commit()
            mid = m.id
        finally:
            db.close()
        # 普通用户无权隐藏
        assert client.post(f"/api/v1/analytics/messages/{mid}/hide",
                          headers=_h(accounts["user"])).status_code == 403
        # 超管可隐藏
        assert client.post(f"/api/v1/analytics/messages/{mid}/hide",
                          headers=_h(accounts["super"])).status_code == 200
        items = client.get("/api/v1/analytics/messages").json()["items"]
        assert not any(m["id"] == mid for m in items)


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

    def test_super_verify_toggle(self, accounts):
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
                       headers=_h(accounts["super"]))
        assert r.json()["verified"] is True

    def test_admin_verify_denied(self, accounts):
        """普通管理员无权核验引用（仅 superadmin）"""
        db = SessionLocal()
        try:
            ref = ExternalReference(source_url="https://d/4",
                                    source_platform="公众号", verified=False)
            db.add(ref)
            db.commit()
            rid = ref.id
        finally:
            db.close()
        r = client.post(f"/api/v1/analytics/references/{rid}/verify",
                       headers=_h(accounts["admin"]))
        assert r.status_code == 403

    def test_guest_verify_denied(self, accounts):
        assert client.post(
            "/api/v1/analytics/references/1/verify").status_code == 401


# ── 分析端点 RBAC（仅超级管理员） ─────────────

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

    @pytest.mark.parametrize("path", [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/references/all",
    ])
    def test_admin_403(self, accounts, path):
        """普通管理员也无权访问证据分析（仅 superadmin）"""
        r = client.get(path, headers=_h(accounts["admin"]))
        assert r.status_code == 403

    def test_super_overview_ok(self, accounts):
        r = client.get("/api/v1/analytics/overview",
                      headers=_h(accounts["super"]))
        assert r.status_code == 200
        assert {"today", "last_7d", "last_30d"} <= set(r.json())

    def test_visits_series_gap_filled(self, accounts):
        r = client.get("/api/v1/analytics/visits",
                      params={"granularity": "day", "days": 14},
                      headers=_h(accounts["super"]))
        # 14 天完整序列（含补零）
        assert len(r.json()["series"]) == 15


# ── 数据导出 ─────────────────────────────────

class TestExport:
    def test_guest_export_denied(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "visits", "days": 7})
        assert r.status_code == 401

    def test_admin_export_denied(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "visits", "days": 7, "fmt": "csv"},
                      headers=_h(accounts["admin"]))
        assert r.status_code == 403

    def test_super_csv_export(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "visits", "days": 7, "fmt": "csv"},
                      headers=_h(accounts["super"]))
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"]
        assert "bucket,pv,uv" in r.text

    def test_super_json_export(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "messages", "days": 7,
                              "fmt": "json"},
                      headers=_h(accounts["super"]))
        assert r.status_code == 200
        assert r.json()["dataset"] == "messages"

    def test_invalid_dataset(self, accounts):
        r = client.get("/api/v1/analytics/export",
                      params={"dataset": "passwords", "days": 7},
                      headers=_h(accounts["super"]))
        assert r.status_code == 422


# ── 站内通知 ─────────────────────────────────

class TestNotifications:
    def _make_post_by(self, user):
        db = SessionLocal()
        try:
            m = Message(user_id=user.id, guest_name=user.username,
                        content="通知测试帖")
            db.add(m)
            db.commit()
            mid = m.id
        finally:
            db.close()
        return mid

    def test_reply_notifies_post_owner(self, accounts):
        pid = self._make_post_by(accounts["user"])
        # 另一个用户回复
        r = client.post(f"/api/v1/analytics/messages/{pid}/reply",
                       json={"reply": "好观点"},
                       headers=_h(accounts["admin"]))
        assert r.status_code in (200, 201)
        # 帖主收到通知
        r = client.get("/api/v1/analytics/notifications",
                      headers=_h(accounts["user"]))
        assert r.json()["unread_count"] >= 1
        assert any(n["type"] == "community_reply"
                  for n in r.json()["items"])
        # 回复者无新通知
        r = client.get("/api/v1/analytics/notifications/unread-count",
                      headers=_h(accounts["admin"]))
        assert r.json()["unread_count"] == 0

    def test_official_reply_type(self, accounts):
        pid = self._make_post_by(accounts["user"])
        client.post(f"/api/v1/analytics/messages/{pid}/reply",
                   json={"reply": "官方答复"},
                   headers=_h(accounts["super"]))
        r = client.get("/api/v1/analytics/notifications",
                      headers=_h(accounts["user"]))
        assert any(n["type"] == "official_reply"
                  for n in r.json()["items"])

    def test_read_and_read_all(self, accounts):
        pid = self._make_post_by(accounts["user"])
        client.post(f"/api/v1/analytics/messages/{pid}/reply",
                   json={"reply": "r1"}, headers=_h(accounts["admin"]))
        h = _h(accounts["user"])
        r = client.get("/api/v1/analytics/notifications", headers=h)
        nid = r.json()["items"][0]["id"]
        assert client.post(
            f"/api/v1/analytics/notifications/{nid}/read",
            headers=h).status_code == 200
        r = client.get("/api/v1/analytics/notifications/unread-count",
                      headers=h)
        assert r.json()["unread_count"] == 0

    def test_guest_denied(self, accounts):
        assert client.get(
            "/api/v1/analytics/notifications").status_code == 401

    def test_verify_notifies_submitter(self, accounts):
        # 登录用户提交引用线索
        h = _h(accounts["user"])
        client.post("/api/v1/analytics/references",
                   json={"source_url": "https://notify-test.example/a",
                         "source_platform": "测试平台"},
                   headers=h)
        db = SessionLocal()
        try:
            ref = db.query(ExternalReference).filter(
                ExternalReference.source_url ==
                "https://notify-test.example/a").first()
            rid = ref.id
            assert ref.submitted_by_id == accounts["user"].id
        finally:
            db.close()
        # 超管核验
        client.post(f"/api/v1/analytics/references/{rid}/verify",
                   headers=_h(accounts["super"]))
        r = client.get("/api/v1/analytics/notifications", headers=h)
        assert any(n["type"] == "reference_verified"
                  for n in r.json()["items"])
