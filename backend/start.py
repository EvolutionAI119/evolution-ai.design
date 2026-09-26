"""启动脚本：使用uvicorn启动FastAPI应用"""
# 先把 .env 全量注入 os.environ：pydantic-settings 只会读取 Settings 声明的字段，
# 而 EVOAI_{PROVIDER}_KEY 这类动态命名的兜底密钥由 security.get_user_api_key 直接
# 通过 os.getenv 读取，因此必须在导入应用前完成加载。
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        # 排除临时/测试脚本与运行产物：这些文件变动不应触发服务重载
        # （_*.py 为一次性调试脚本，约定见项目 .gitignore）
        reload_excludes=[
            "_*.py", "test_*.py",
            "tests/*",
            "*.db", "*.log", "*.json", "*.sqlite3",
            "uploads/*", "../data/*",
        ],
        log_level=settings.LOG_LEVEL.lower(),
        # 响应头审计：避免向客户端暴露 "server: uvicorn" 信息
        server_header=not settings.HIDE_SERVER_HEADER,
        # 去掉 x-powered-by / asgi 类似的信息头
        headers=[],
    )
