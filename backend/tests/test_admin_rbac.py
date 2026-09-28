"""分级权限（RBAC）回归测试。

覆盖四级边界：
- 游客：admin 端点 401；写项目端点 401
- 普通用户：admin 端点 403；仅能管理自己的项目（越权改他人项目 403）
- 管理员：可看用户列表/登录记录；账户修复动作 403；用户列表不泄露敏感字段
- 超级管理员：账户修复全部可用、写审计日志、可读后端错误日志；自我保护规则生效
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import (AdminAuditLog, LoginRecord, Project, SessionLocal,
                          User, init_db)
from app.security import create_access_token, hash_password

client = TestClient(app)


# ── 测试账户（直接入库，用完即清） ───────────

TEST_EMAILS = [
    "rbac_user@test.local", "rbac_admin@test.local",
    "rbac_super@test.local", "rbac_a@test.local", "rbac_b@test.local",
]


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
    users = {}
    try:
        for name, role in [("user", "user"), ("admin", "admin"),
                           ("super", "superadmin"),
                           ("a", "user"), ("b", "user")]:
            users[name] = _make_user(db, f"rbac_{name}@test.local", role)
        yield users
        # 清理：测试项目 + 审计/登录记录 + 用户
        for u in db.query(User).filter(User.email.in_(TEST_EMAILS)).all():
            db.query(Project).filter(Project.user_id == u.id).delete()
            db.query(AdminAuditLog).filter(
                AdminAuditLog.admin_id == u.id).delete()
            db.query(LoginRecord).filter(LoginRecord.user_id == u.id).delete()
        db.query(LoginRecord).filter(
            LoginRecord.email.in_(TEST_EMAILS)).delete()
        for u in db.query(User).filter(User.email.in_(TEST_EMAILS)).all():
            db.delete(u)
        db.commit()
    finally:
        db.close()


def _h(user):
    token = create_access_token({"sub": str(user.id), "email": user.email,
                                 "role": user.role})
    return {"Authorization": f"Bearer {token}"}


# ── 游客级别 ─────────────────────────────────

class TestGuest:
    def test_admin_users_requires_login(self, accounts):
        assert client.get("/api/v1/admin/users").status_code == 401

    def test_admin_records_requires_login(self, accounts):
        assert client.get("/api/v1/admin/login-records").status_code == 401

    def test_project_create_requires_login(self, accounts):
        r = client.post("/api/v1/projects/", json={"name": "guest x"})
        assert r.status_code == 401

    def test_public_pages_still_open(self, accounts):
        # 游客仍可浏览项目列表与元数据
        assert client.get("/api/v1/projects/").status_code == 200
        assert client.get("/api/v1/car/components").status_code == 200


# ── 普通用户级别 ─────────────────────────────

class TestRegularUser:
    def test_admin_endpoints_forbidden(self, accounts):
        h = _h(accounts["user"])
        assert client.get("/api/v1/admin/users", headers=h).status_code == 403
        assert client.get(
            "/api/v1/admin/login-records", headers=h).status_code == 403

    def test_can_create_own_project(self, accounts):
        r = client.post("/api/v1/projects/",
                        json={"name": "own p"}, headers=_h(accounts["user"]))
        assert r.status_code == 201
        assert r.json()["user_id"] == accounts["user"].id

    def test_cannot_modify_other_project(self, accounts):
        a, b = accounts["a"], accounts["b"]
        pid = client.post("/api/v1/projects/",
                          json={"name": "a p"}, headers=_h(a)).json()["id"]
        # B 无权修改/删除 A 的项目
        assert client.put(f"/api/v1/projects/{pid}",
                          json={"name": "hijack"},
                          headers=_h(b)).status_code == 403
        assert client.delete(f"/api/v1/projects/{pid}",
                             headers=_h(b)).status_code == 403
        # A 本人可以修改
        assert client.put(f"/api/v1/projects/{pid}",
                          json={"name": "a p2"},
                          headers=_h(a)).status_code == 200


# ── 管理员级别 ───────────────────────────────

class TestAdmin:
    def test_can_view_users(self, accounts):
        r = client.get("/api/v1/admin/users", headers=_h(accounts["admin"]))
        assert r.status_code == 200
        emails = [u["email"] for u in r.json()]
        assert "rbac_admin@test.local" in emails

    def test_user_list_no_sensitive_fields(self, accounts):
        r = client.get("/api/v1/admin/users", headers=_h(accounts["admin"]))
        item = next(u for u in r.json()
                    if u["email"] == "rbac_user@test.local")
        assert "password_hash" not in item
        assert "api_keys" not in item
        assert item["role"] == "user"

    def test_can_view_login_records(self, accounts):
        # 制造一条失败登录
        client.post("/api/v1/auth/login", json={
            "email": "rbac_user@test.local", "password": "wrong-pass"})
        r = client.get(
            "/api/v1/admin/login-records",
            params={"email": "rbac_user@test.local"},
            headers=_h(accounts["admin"]))
        assert r.status_code == 200
        reasons = [row["reason"] for row in r.json()]
        assert "bad_credentials" in reasons

    def test_account_repair_forbidden_for_admin(self, accounts):
        target = accounts["user"]
        h = _h(accounts["admin"])
        assert client.post(f"/api/v1/admin/users/{target.id}/active",
                           json={"is_active": False},
                           headers=h).status_code == 403
        assert client.post(f"/api/v1/admin/users/{target.id}/reset-password",
                           json={"new_password": "newpass123"},
                           headers=h).status_code == 403
        assert client.post(f"/api/v1/admin/users/{target.id}/role",
                           json={"role": "admin"},
                           headers=h).status_code == 403


# ── 超级管理员级别 ───────────────────────────

class TestSuperAdmin:
    def test_set_active_and_audit(self, accounts):
        target, sup = accounts["user"], accounts["super"]
        r = client.post(f"/api/v1/admin/users/{target.id}/active",
                        json={"is_active": False}, headers=_h(sup))
        assert r.status_code == 200
        assert r.json()["is_active"] is False
        db = SessionLocal()
        try:
            log = (db.query(AdminAuditLog)
                   .filter(AdminAuditLog.admin_id == sup.id,
                           AdminAuditLog.action == "set_active").first())
            assert log is not None
            assert '"is_active": false' in log.detail_json
        finally:
            db.close()

    def test_reset_password_and_audit(self, accounts):
        target, sup = accounts["user"], accounts["super"]
        r = client.post(f"/api/v1/admin/users/{target.id}/reset-password",
                        json={"new_password": "brandnew99"}, headers=_h(sup))
        assert r.status_code == 200
        # 新密码可登录
        ok = client.post("/api/v1/auth/login", json={
            "email": target.email, "password": "brandnew99"})
        assert ok.status_code == 200
        db = SessionLocal()
        try:
            log = (db.query(AdminAuditLog)
                   .filter(AdminAuditLog.admin_id == sup.id,
                           AdminAuditLog.action == "reset_password").first())
            # 审计详情不得包含明文密码
            assert log is not None
            assert "brandnew99" not in log.detail_json
        finally:
            db.close()

    def test_set_role_and_audit(self, accounts):
        target, sup = accounts["user"], accounts["super"]
        r = client.post(f"/api/v1/admin/users/{target.id}/role",
                        json={"role": "admin"}, headers=_h(sup))
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
        assert r.json()["is_admin"] is True

    def test_invalid_role_rejected(self, accounts):
        target, sup = accounts["user"], accounts["super"]
        r = client.post(f"/api/v1/admin/users/{target.id}/role",
                        json={"role": "hacker"}, headers=_h(sup))
        assert r.status_code == 422

    def test_backend_errors_visible(self, accounts):
        r = client.get("/api/v1/admin/backend-errors",
                       headers=_h(accounts["super"]))
        assert r.status_code == 200
        assert "content" in r.json()

    def test_audit_logs_list(self, accounts):
        sup = accounts["super"]
        client.post(f"/api/v1/admin/users/{accounts['user'].id}/active",
                    json={"is_active": True}, headers=_h(sup))
        r = client.get("/api/v1/admin/audit-logs", headers=_h(sup))
        assert r.status_code == 200
        assert any(row["action"] == "set_active" for row in r.json())

    def test_self_protection(self, accounts):
        sup = accounts["super"]
        # 不能停用自己
        r = client.post(f"/api/v1/admin/users/{sup.id}/active",
                        json={"is_active": False}, headers=_h(sup))
        assert r.status_code == 400
        # 不能降低自己角色
        r = client.post(f"/api/v1/admin/users/{sup.id}/role",
                        json={"role": "user"}, headers=_h(sup))
        assert r.status_code == 400

    def test_admin_cannot_reach_super_endpoints(self, accounts):
        h = _h(accounts["admin"])
        assert client.get("/api/v1/admin/audit-logs",
                          headers=h).status_code == 403
        assert client.get("/api/v1/admin/backend-errors",
                          headers=h).status_code == 403
