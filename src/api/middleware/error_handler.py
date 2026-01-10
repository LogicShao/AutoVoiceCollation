"""
API 错误处理中间件

提供统一的错误处理和响应格式
"""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.exceptions import (
    ASRError,
    AutoVoiceCollationError,
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    ResourceNotFoundError,
    TaskCancelledException,
    TaskNotFoundError,
    ValidationError,
)
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


async def auto_voice_collation_error_handler(
    request: Request, exc: AutoVoiceCollationError
) -> JSONResponse:
    """
    统一处理项目自定义异常

    Args:
        request: FastAPI 请求对象
        exc: 项目自定义异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    # 记录错误日志
    logger.error(
        f"Error handling request: {exc.code}",
        exc_info=True,
        extra={
            "error_code": exc.code,
            "error_type": exc.__class__.__name__,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details,
        },
    )

    # 根据异常类型确定 HTTP 状态码
    status_code = _determine_status_code(exc)

    # 返回统一格式的错误响应
    return JSONResponse(status_code=status_code, content=exc.to_dict())


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    处理 Pydantic 验证错误

    Args:
        request: FastAPI 请求对象
        exc: Pydantic 验证异常

    Returns:
        JSONResponse: 格式化的验证错误响应
    """
    # 记录详细的验证错误信息
    logger.error(
        f"Validation error: {request.url.path}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
            "body": exc.body if hasattr(exc, "body") else None,
        },
    )
    # 同时打印到控制台以便调试
    logger.error(f"验证错误详情: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "请求参数验证失败",
            "code": "VALIDATION_ERROR",
            "type": "RequestValidationError",
            "details": {"validation_errors": exc.errors()},
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    处理 HTTP 异常

    Args:
        request: FastAPI 请求对象
        exc: HTTP 异常

    Returns:
        JSONResponse: 格式化的 HTTP 错误响应
    """
    # 定义需要静默处理的探测请求路径
    silent_paths = [
        "/.well-known/",  # 浏览器/工具的标准探测路径
        "/favicon.ico",  # 浏览器自动请求的图标
        "/robots.txt",  # 搜索引擎爬虫
    ]

    # 检查是否为探测请求
    is_probe_request = any(request.url.path.startswith(path) for path in silent_paths)

    # 对于 400 错误，记录更详细的信息
    if exc.status_code == 400:
        logger.error(
            f"HTTP {exc.status_code}: {request.url.path} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "detail": exc.detail,
            },
        )
    # 对于探测请求的 404,不记录日志以避免噪音
    elif exc.status_code == 404 and is_probe_request:
        pass  # 静默处理,不记录日志
    else:
        logger.warning(
            f"HTTP {exc.status_code}: {request.url.path}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            },
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": f"HTTP_{exc.status_code}",
            "type": "HTTPException",
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    处理未捕获的通用异常

    Args:
        request: FastAPI 请求对象
        exc: 通用异常

    Returns:
        JSONResponse: 格式化的错误响应
    """
    # 记录完整的错误堆栈
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": exc.__class__.__name__,
        },
    )

    # 在生产环境中不暴露详细的错误信息
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "服务器内部错误",
            "code": "INTERNAL_SERVER_ERROR",
            "type": "Exception",
            "details": {"message": str(exc) if logger.level == "DEBUG" else "请联系管理员"},
        },
    )


def _determine_status_code(exc: AutoVoiceCollationError) -> int:
    """
    根据异常类型确定 HTTP 状态码

    Args:
        exc: 项目自定义异常

    Returns:
        int: HTTP 状态码
    """
    # 404 - 资源不存在
    if isinstance(exc, (TaskNotFoundError, ResourceNotFoundError)):
        return status.HTTP_404_NOT_FOUND

    # 422 - 验证错误
    if isinstance(exc, ValidationError):
        return status.HTTP_422_UNPROCESSABLE_ENTITY

    # 401 - 认证失败
    if isinstance(exc, LLMAuthenticationError):
        return status.HTTP_401_UNAUTHORIZED

    # 429 - 速率限制
    if isinstance(exc, LLMRateLimitError):
        return status.HTTP_429_TOO_MANY_REQUESTS

    # 499 - 客户端取消请求（非标准，但常用）
    if isinstance(exc, TaskCancelledException):
        return 499

    # 503 - 服务不可用（ASR/LLM 服务错误）
    if isinstance(exc, (ASRError, LLMError)):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    # 500 - 其他错误
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def register_exception_handlers(app):
    """
    注册所有异常处理器到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
    """
    # 项目自定义异常
    app.add_exception_handler(AutoVoiceCollationError, auto_voice_collation_error_handler)

    # Pydantic 验证错误
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # HTTP 异常
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 通用异常（最后兜底）
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("异常处理器已注册")
