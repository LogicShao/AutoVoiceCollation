import asyncio
import os
import uuid
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from src.api.inference_queue import get_inference_queue
from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)
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


async def _startup():
    queue = _get_or_create_queue()
    await queue.start()
    logger.info("推理队列已启动")


async def _shutdown():
    global _queue
    if _queue is not None:
        await _queue.stop()
        _queue = None
        logger.info("推理队列已停止")


def main():
    asyncio.run(_startup())
    try:
        mcp.run(transport="stdio")
    finally:
        asyncio.run(_shutdown())


if __name__ == "__main__":
    main()
