"""Structured error handling middleware for FastAPI."""

from __future__ import annotations

import logging
import time
import traceback
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.responses import ApiError, ApiResponse

logger = logging.getLogger(__name__)


def _error_response(
    code: str,
    message: str,
    http_status: int,
    details: dict | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    resp = ApiResponse(
        error=ApiError(code=code, message=message, details=details or {}),
        request_id=request_id,
    )
    return JSONResponse(status_code=http_status, content=resp.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return _error_response(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            http_status=exc.status_code,
            request_id=request_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        errors = exc.errors()
        logger.warning("Validation error on %s %s: %s", request.method, request.url.path, errors)
        return _error_response(
            code="VALIDATION_ERROR",
            message="请求参数校验失败",
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": errors},
            request_id=request_id,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error(
            "Unhandled exception on %s %s: %s\n%s",
            request.method,
            request.url.path,
            exc,
            traceback.format_exc(),
        )
        return _error_response(
            code="INTERNAL_ERROR",
            message="服务器内部错误，请稍后重试",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
        )


def register_request_middleware(app: FastAPI, metrics_collector=None) -> None:
    """Add request ID, timing, and metrics middleware."""

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid4().hex[:16])
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"

        # Record metrics
        is_error = response.status_code >= 400
        if metrics_collector is not None:
            metrics_collector.record_request(elapsed_ms, is_error=is_error)

        # Log request (skip noisy health checks)
        if request.url.path not in ("/api/health", "/api/metrics"):
            logger.info(
                "%s %s → %d (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )

        return response
