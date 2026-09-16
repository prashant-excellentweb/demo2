import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(
        "Buddy Chat %s starting | env=%s provider=%s model=%s",
        __version__,
        settings.ENVIRONMENT,
        settings.AI_PROVIDER,
        settings.ai_model,
    )
    yield
    logger.info("Buddy Chat shutting down")


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        """Single mapping from domain errors to status codes.

        Services stay HTTP-agnostic and clients always receive the same
        `{"detail": "..."}` shape.
        """
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        message = first.get("msg", "The submitted data is invalid.")
        # Pydantic prefixes messages it raised itself; strip it for display.
        message = message.removeprefix("Value error, ")
        return JSONResponse(status_code=422, content={"detail": message})


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built React bundle when it exists.

    In development the Vite dev server owns the UI and proxies `/api`, so a
    missing `dist/` directory is expected and not an error.
    """
    dist = Path(settings.FRONTEND_DIST_DIR)
    index_file = dist / "index.html"
    if not index_file.is_file():
        logger.info("No frontend build found at %s; serving API only.", dist)
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    dist_root = dist.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> Response:
        # This catch-all runs after the API router, so an unmatched /api path is
        # a genuine 404. Returning the HTML shell there would hand the client
        # markup where it expects JSON and hide the real problem.
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found."})

        # Serve real files (favicon, manifest, ...) but never follow a path that
        # escapes the build directory.
        if full_path:
            candidate = (dist_root / full_path).resolve()
            if candidate.is_relative_to(dist_root) and candidate.is_file():
                return FileResponse(candidate)

        # Client-side routes such as /login have no server counterpart, so
        # anything else returns the shell and lets React Router resolve it.
        return FileResponse(index_file)


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Buddy Chat API",
        version=__version__,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    if not settings.is_production:
        # Only needed while the Vite dev server runs on a different origin.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    _register_error_handlers(app)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict:
        return {"status": "ok", "version": __version__}

    app.include_router(api_router)
    _mount_frontend(app)
    return app


app = create_app()
