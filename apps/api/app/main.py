import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import register_error_handlers, register_request_middleware
from app.core.security import validate_security_config
from app.modules.admin.router import router as admin_router
from app.modules.agent.router import router as agent_router
from app.modules.agent_tokens.router import router as agent_tokens_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.service import seed_admin_user
from app.modules.data_mgmt.router import router as data_mgmt_router
from app.modules.feed.router import router as feed_router
from app.modules.health.router import metrics as metrics_collector
from app.modules.health.router import router as health_router
from app.modules.plugins.router import router as plugins_router
from app.modules.preferences.router import router as preferences_router
from app.modules.proxy.router import router as proxy_router
from app.modules.scheduler.service import scheduler_service
from app.modules.search.router import router as search_router
from app.modules.sources.router import router as sources_router
from app.modules.upload.router import router as upload_router
from app.modules.users.router import router as users_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Security validation on startup
    validate_security_config(strict=False)

    # Seed admin user on startup
    db = SessionLocal()
    try:
        seed_admin_user(db)
    except Exception:
        logger.warning("Failed to seed admin user (database may not be ready)")
    finally:
        db.close()
    if settings.scheduler_enabled:
        scheduler_service.start()
    logger.info("Application startup complete (v%s)", settings.app_version)
    try:
        yield
    finally:
        scheduler_service.stop()
        logger.info("Application shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_request_middleware(app, metrics_collector)
    register_error_handlers(app)

    @app.middleware("http")
    async def strip_api_trailing_slash(request: Request, call_next):
        path = request.url.path
        if len(path) > 1 and path.endswith("/") and path.startswith("/api"):
            new_path = path.rstrip("/")
            if new_path:
                from starlette.responses import RedirectResponse
                return RedirectResponse(url=str(request.url.replace(path=new_path)), status_code=307)
        return await call_next(request)

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(users_router, prefix="/api/users", tags=["users"])
    app.include_router(sources_router, prefix="/api/sources", tags=["sources"])
    app.include_router(feed_router, prefix="/api/feed", tags=["feed"])
    app.include_router(search_router, prefix="/api/search", tags=["search"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    app.include_router(agent_router, prefix="/api/agent", tags=["agent"])
    app.include_router(agent_tokens_router, prefix="/api/agent-tokens", tags=["agent-tokens"])
    app.include_router(preferences_router, prefix="/api/preferences", tags=["preferences"])
    app.include_router(proxy_router, prefix="/api/proxy", tags=["proxy"])
    app.include_router(plugins_router, prefix="/api/plugins", tags=["plugins"])
    app.include_router(data_mgmt_router, prefix="/api/data-mgmt", tags=["data-management"])
    app.include_router(upload_router, prefix="/api/upload", tags=["upload"])

    # Serve uploaded files as static files
    uploads_dir = settings.uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.uploads_url_path,
        StaticFiles(directory=str(uploads_dir)),
        name="uploads",
    )

    # Serve frontend static files
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve frontend SPA - all non-API routes return index.html"""
            file_path = static_dir / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(static_dir / "index.html"))

    return app


app = create_app()
