import asyncio
import logging
import os
import sys
import uuid
from contextlib import suppress
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from src.api.inference_queue import get_inference_queue
from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


def _fix_mcp_logging():
    """Reconfigure logger for MCP stdio transport.

    MCP uses stdout for JSONRPC protocol — logger must NOT write to stdout.
    Redirect console handler to stderr and make it error-tolerant so shutdown
    after transport close doesn't crash.
    """
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
            handler.stream = sys.stderr

    # Silence handleError tracebacks on closed stream
    logging.raiseExceptions = False


_fix_mcp_logging()
config = get_config()

mcp = FastMCP("AutoVoiceCollation")

tasks: dict = {}
_queue = None


def _get_or_create_queue():
    global _queue
    if _queue is None:
        _queue = get_inference_queue()
    return _queue


async def _submit_task(task_type: str, task_data: dict) -> str:
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "pending",
        "message": "任务已提交，等待处理",
        "created_at": datetime.now().isoformat(),
    }
    queue = _get_or_create_queue()
    await queue.submit_task(
        task_id=task_id,
        task_type=task_type,
        task_data=task_data,
        tasks_store=tasks,
    )
    return task_id


@mcp.tool()
async def process_bilibili(url: str) -> dict:
    """处理B站视频链接，返回 task_id 用于查询状态"""
    if not url.strip():
        return {"error": "URL 不能为空"}

    task_id = await _submit_task(
        "bilibili",
        {
            "video_url": url.strip(),
            "llm_api": config.llm.llm_server,
            "temperature": config.llm.llm_temperature,
            "max_tokens": config.llm.llm_max_tokens,
            "text_only": False,
            "summarize": False,
        },
    )
    return {"task_id": task_id, "status": "pending"}


@mcp.tool()
async def process_audio(file_path: str) -> dict:
    """处理本地音频/视频文件，返回 task_id"""
    if not file_path.strip():
        return {"error": "文件路径不能为空"}

    file_path = file_path.strip()
    if not os.path.isfile(file_path):
        return {"error": f"文件不存在: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".mp3", ".wav", ".m4a", ".flac", ".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv"):
        return {"error": f"不支持的文件格式: {ext}"}

    task_id = await _submit_task(
        "audio",
        {
            "audio_path": file_path,
            "llm_api": config.llm.llm_server,
            "temperature": config.llm.llm_temperature,
            "max_tokens": config.llm.llm_max_tokens,
            "text_only": False,
            "summarize": False,
        },
    )
    return {"task_id": task_id, "status": "pending", "file": os.path.basename(file_path)}


@mcp.tool()
async def process_batch(urls: list[str]) -> dict:
    """批量处理多个B站视频链接，返回 task_id"""
    if not urls:
        return {"error": "URL 列表不能为空"}

    clean_urls = [u.strip() for u in urls if u.strip()]
    if not clean_urls:
        return {"error": "没有有效的 URL"}

    task_id = await _submit_task(
        "batch",
        {
            "urls": "\n".join(clean_urls),
            "llm_api": config.llm.llm_server,
            "temperature": config.llm.llm_temperature,
            "max_tokens": config.llm.llm_max_tokens,
            "text_only": False,
            "summarize": False,
        },
    )
    return {"task_id": task_id, "status": "pending", "count": len(clean_urls)}


@mcp.tool()
async def get_task_status(task_id: str) -> dict:
    """查询任务状态和结果"""
    if task_id not in tasks:
        return {"error": f"任务不存在: {task_id}"}

    task = tasks[task_id]
    return {
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "message": task.get("message", ""),
        "created_at": task.get("created_at", ""),
        "completed_at": task.get("completed_at", ""),
        "result": task.get("result"),
        "error": task.get("error"),
    }


@mcp.tool()
async def cancel_task(task_id: str) -> dict:
    """取消正在处理的任务"""
    if task_id not in tasks:
        return {"error": f"任务不存在: {task_id}"}

    from src.utils.helpers.task_manager import get_task_manager

    tm = get_task_manager()
    if tm.task_exists(task_id):
        tm.cancel_task(task_id)
        tasks[task_id]["status"] = "cancelled"
        tasks[task_id]["message"] = "任务已取消"
        return {"task_id": task_id, "status": "cancelled"}

    if tasks[task_id]["status"] in ("completed", "failed", "cancelled"):
        return {"task_id": task_id, "status": tasks[task_id]["status"], "message": "任务已结束，无法取消"}

    tasks[task_id]["status"] = "cancelled"
    tasks[task_id]["message"] = "任务已取消"
    return {"task_id": task_id, "status": "cancelled"}


@mcp.tool()
async def generate_mindmap(task_id: str) -> dict:
    """为已完成的任务生成思维导图，返回 Mermaid + JSON 文件路径"""
    if task_id not in tasks:
        return {"error": f"任务不存在: {task_id}"}

    task = tasks[task_id]
    if task.get("status") != "completed":
        return {"error": f"任务尚未完成，当前状态: {task.get('status')}"}

    result = task.get("result", {})
    text = result.get("text") or result.get("transcript") or ""
    title = result.get("title") or task.get("message", "")

    if not text:
        return {"error": "任务结果中没有可用的文本内容"}

    from src.services.mindmap import export_mindmap_to_files
    from src.services.mindmap import generate_mindmap as _gen

    output_dir = result.get("output_dir", f"./out/{task_id}")
    output = await _gen(text=text, title=title)
    files = export_mindmap_to_files(output, output_dir)

    return {
        "task_id": task_id,
        "title": title,
        "node_count": output.node_count,
        "files": files,
        "mermaid_preview": output.root.model_dump() if output.root.children else None,
    }


@mcp.tool()
async def analyze_video(url: str) -> dict:
    """分析B站视频：一键完成转写+LLM结构化分析，返回 title/summary/key_points/segments"""
    if not url.strip():
        return {"error": "URL 不能为空"}

    task_id = await _submit_task(
        "analyze_video",
        {
            "video_url": url.strip(),
            "llm_api": config.llm.llm_server,
            "temperature": config.llm.llm_temperature,
            "max_tokens": config.llm.llm_max_tokens,
        },
    )
    return {"task_id": task_id, "status": "pending", "message": "分析任务已提交，请通过 get_task_status 获取结果"}


async def _startup():
    queue = _get_or_create_queue()
    await queue.start()
    with suppress(ValueError):
        logger.info("推理队列已启动")


async def _shutdown():
    global _queue
    if _queue is not None:
        await _queue.stop()
        _queue = None
        with suppress(ValueError):
            logger.info("推理队列已停止")


def main():
    asyncio.run(_startup())
    try:
        mcp.run(transport="stdio")
    finally:
        asyncio.run(_shutdown())


if __name__ == "__main__":
    main()
