"""独立管理后台静态托管测试（Admin 模块已移出公开前端，由后端 /admin 提供）"""
from pathlib import Path


def test_admin_console_index_served(client):
    """GET /admin/ 返回独立后台入口 HTML"""
    r = client.get("/admin/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert b"admin-app" in r.content


def test_admin_csp_allows_eval_only_for_admin_docs(client):
    """vue-i18n 编译器需要 unsafe-eval：仅 /admin 文档放宽，公开 API 仍严格"""
    admin_resp = client.get("/admin/")
    assert "unsafe-eval" in admin_resp.headers["content-security-policy"]

    api_resp = client.get("/api/v1/health")
    csp = api_resp.headers.get("content-security-policy", "")
    assert "unsafe-eval" not in csp


def test_admin_console_assets_on_disk():
    """构建产物（index.html + assets/*.js）必须就位，保证后端镜像自包含"""
    admin_dir = Path(__file__).resolve().parents[1] / "app" / "static" / "admin"
    assert admin_dir.is_dir()
    assert (admin_dir / "index.html").is_file()
    assert list((admin_dir / "assets").glob("*.js"))
