"""FastAPI主入口 - 专利分类Web服务"""

import sys
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes import config_router, classify_router, rules_router, upload_router

# 创建应用
app = FastAPI(
    title="Patsona 专利分类服务",
    description="基于递进式分层分类的专利分类Web界面",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由（优先级高于静态文件）
app.include_router(config_router)
app.include_router(classify_router)
app.include_router(rules_router)
app.include_router(upload_router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 前端静态文件目录（打包模式）
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"


class SPAMiddleware(BaseHTTPMiddleware):
    """SPA 前端中间件 - 只对非API路径返回前端页面

    - /api/* 路径：交给API路由处理
    - /assets/* 路径：返回静态资源
    - 其他路径：返回 index.html（SPA前端）
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # API路径和health直接交给路由
        if path.startswith("/api/") or path == "/health" or path == "/docs" or path == "/openapi.json":
            return await call_next(request)

        # 前端静态文件存在时才处理
        if not (STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists()):
            return await call_next(request)

        # 静态资源文件
        if path.startswith("/assets/"):
            file_path = STATIC_DIR / path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))

        # 其他路径：返回 index.html（SPA路由）
        if path == "/" or not (STATIC_DIR / path.lstrip("/")).exists():
            return FileResponse(str(STATIC_DIR / "index.html"))

        # 尝试返回具体文件
        file_path = STATIC_DIR / path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        return FileResponse(str(STATIC_DIR / "index.html"))


# 挂载SPA中间件
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    app.add_middleware(SPAMiddleware)
