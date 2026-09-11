# src/core/exceptions.py
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


def register_exception_handlers(app):
    """在 main.py 中调用，注册所有全局异常处理器"""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Pydantic 参数校验失败 → 422"""
        logger.warning(f"参数校验失败 {request.url.path}: {exc.errors()}")
        # 简化错误信息，只保留第一个错误
        first_error = exc.errors()[0] if exc.errors() else {}
        msg = first_error.get("msg", "请求参数错误")
        field = ".".join(str(x) for x in first_error.get("loc", []))
        detail = f"参数错误 ({field}): {msg}" if field else msg
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """所有 HTTPException（包括业务里抛的）→ 保持状态码，统一格式"""
        if exc.status_code >= 500:
            logger.error(f"HTTP {exc.status_code} {request.url.path}: {exc.detail}")
        else:
            logger.info(f"HTTP {exc.status_code} {request.url.path}: {exc.detail}")

        # 429 是限流触发，替换成中文提示
        if exc.status_code == 429:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"}
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None)
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """兜底：任何未预料的异常 → 500，不泄露堆栈"""
        logger.error(f"未处理异常 {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后再试"}
        )