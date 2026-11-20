"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError, ProgrammingError, TimeoutError as DatabaseTimeoutError
from starlette.responses import Response

BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db import session
from app.db.base import Base
from app.services.exceptions import (
    AIResponseValidationError,
    LLMRequestError,
    ResourceNotFoundError,
    ServiceError,
    StorageUnavailableError,
    ValidationError,
)

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)


def initialize_local_database() -> None:
    engine = session.engine
    if not engine.url.database or engine.url.database == ":memory:":
        Base.metadata.create_all(bind=engine)
        return
    Path(engine.url.database).parent.mkdir(parents=True, exist_ok=True)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    config = Config(str(Path(BACKEND_DIR) / "alembic.ini"))
    config.attributes["database_url"] = engine.url.render_as_string(hide_password=False)
    config.attributes["configure_logger"] = False
    if "alembic_version" not in tables and "patients" in tables:
        required = {"patients", "medical_histories", "medications", "allergies", "symptoms", "medical_reports", "ai_analyses"}
        if not required.issubset(tables):
            raise RuntimeError("The local SQLite schema is incomplete. Back it up and verify its migration baseline.")
        command.stamp(config, "20260803_0001" if "users" in tables else "20260728_0001")
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the local SQLite database at startup; hosted schemas use Alembic."""
    if session.sqlite:
        initialize_local_database()
    for issue in settings.storage_issues():
        logger.warning("Storage readiness: %s", issue)
    logger.info("Starting %s", settings.project_name)
    yield
    logger.info("Shutting down %s", settings.project_name)


app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    servers=[{"url": settings.api_v1_prefix, "description": "API v1"}],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


def custom_openapi() -> dict[str, object]:
    """Expose OpenAPI paths without the version prefix while preserving the actual API base URL."""
    if app.openapi_schema is not None:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
    )

    paths = openapi_schema.get("paths", {})
    normalized_paths: dict[str, object] = {}
    for path, path_item in paths.items():
        if path.startswith(settings.api_v1_prefix):
            normalized_paths[path.removeprefix(settings.api_v1_prefix)] = path_item
        else:
            normalized_paths[path] = path_item

    openapi_schema["paths"] = normalized_paths
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.middleware("http")
async def log_api_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log request metadata without recording payloads or secrets."""
    try:
        response = await call_next(request)
    except Exception as exc:
        if settings.debug:
            raise
        response = await unhandled_exception_handler(request, exc)
    if request.url.path.startswith(f"{settings.api_v1_prefix}/"):
        response.headers.setdefault("Cache-Control", "private, no-store")
    logger.info(
        "%s %s completed with %s",
        request.method,
        route_template(request),
        response.status_code,
    )
    return response


def route_template(request: Request) -> str:
    return getattr(request.scope.get("route"), "path", "<unmatched>")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Convert FastAPI validation failures into the documented error envelope."""
    logger.warning("Validation error on %s %s", request.method, route_template(request))
    errors: dict[str, list[str]] = {}
    for error in exc.errors():
        field_name = ".".join(str(part) for part in error.get("loc", ("body",)))
        message = str(error.get("msg", "Validation failed."))
        errors.setdefault(field_name, []).append(message)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation failed.",
            "errors": errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return the documented response envelope for expected HTTP errors."""
    logger.warning("HTTP %s on %s %s", exc.status_code, request.method, route_template(request))
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "success": False,
            "message": str(exc.detail),
            "errors": {},
        },
    )


@app.exception_handler(ServiceError)
async def service_exception_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """Translate service-layer exceptions into safe API responses."""
    logger.warning("%s on %s %s", type(exc).__name__, request.method, route_template(request))
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, ResourceNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, StorageUnavailableError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, AIResponseValidationError):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, LLMRequestError):
        status_code = exc.status_code

    content = {"success": False, "message": str(exc), "errors": {"detail": [str(exc)]}}
    if isinstance(exc, LLMRequestError):
        content["error"] = exc.code

    return JSONResponse(
        status_code=status_code,
        content=content,
    )


@app.exception_handler(OperationalError)
@app.exception_handler(ProgrammingError)
@app.exception_handler(DatabaseTimeoutError)
async def database_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    original = getattr(exc, "orig", None)
    missing_schema = getattr(original, "sqlstate", None) in {"42P01", "42703"}
    if session.sqlite and isinstance(exc, OperationalError):
        missing_schema = str(original).startswith(("no such table:", "no such column:"))
    if missing_schema:
        logger.error("Database schema is incomplete on %s %s. Check Alembic migration head.",
                     request.method, route_template(request))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"success": False, "error": "database_schema_incomplete",
                     "message": "The database schema is incomplete. Contact your administrator.", "errors": {}},
        )
    if isinstance(exc, ProgrammingError):
        return await unhandled_exception_handler(request, exc)
    logger.error("Database unavailable on %s %s (%s)", request.method, route_template(request), type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"success": False, "error": "database_unavailable",
                 "message": "Database temporarily unavailable. Try again shortly.", "errors": {}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log the error type and route without logging exception contents."""
    logger.error("Unhandled %s on %s %s", type(exc).__name__, request.method, route_template(request))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "errors": {},
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
