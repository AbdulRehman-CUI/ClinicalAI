"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
import sys
from pathlib import Path

from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.responses import Response
import uvicorn

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
for path in (ROOT_DIR, BACKEND_DIR):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.exceptions import (
    AIResponseValidationError,
    AIServiceUnavailableError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    servers=[{"url": settings.api_v1_prefix, "description": "API v1"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
async def startup_event() -> None:
    """Ensure deployment directories exist before the service starts serving traffic."""
    upload_directory = settings.resolve_upload_directory()
    upload_directory.mkdir(parents=True, exist_ok=True)

    database_path = settings.resolve_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Starting %s on %s:%s", settings.project_name, settings.host, settings.port)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Log shutdown events for container and process lifecycle visibility."""
    logger.info("Shutting down %s", settings.project_name)


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


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


@app.middleware("http")
async def log_api_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log request metadata without recording payloads or secrets."""
    response = await call_next(request)
    logger.info(
        "%s %s completed with %s",
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Convert FastAPI validation failures into the documented error envelope."""
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
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
    logger.warning("HTTP error on %s %s: %s", request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "errors": {},
        },
    )


@app.exception_handler(ServiceError)
async def service_exception_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """Translate service-layer exceptions into safe API responses."""
    logger.warning("Service error on %s %s: %s", request.method, request.url.path, exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, ResourceNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, AIServiceUnavailableError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, AIResponseValidationError):
        status_code = status.HTTP_502_BAD_GATEWAY

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": str(exc),
            "errors": {"detail": [str(exc)]},
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log unexpected errors while returning a safe API response."""
    logger.exception("Unhandled backend error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "errors": {},
        },
    )
