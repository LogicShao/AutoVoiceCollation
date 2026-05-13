"""MCP Server — 薄适配层，将 MCP Tool 调用转发到本地 FastAPI 服务"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)
config = get_config()

API_BASE = os.getenv("AVC_API_URL", "http://127.0.0.1:8000")

mcp = FastMCP("AutoVoiceCollation")


async def _api(method: str, path: str, **kwargs) -> dict:
    """通用 HTTP 代理调用，返回 JSON dict 或带 error 的 dict"""
    url = f"{API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            resp = await client.request(method, url, **kwargs)
            return resp.json()
    except httpx.ConnectError:
        return {"error": f"无法连接到 AVC API 服务 ({API_BASE})，请确认 api.py 已启动"}
    except Exception as e:
        return {"error": f"API 请求失败: {e}"}


@mcp.tool()
async def process_bilibili(url: str) -> dict:
    """处理B站视频链接，返回 task_id 用于查询状态"""
    if not url.strip():
        return {"error": "URL 不能为空"}
    return await _api("POST", "/api/v1/process/bilibili", json={"video_url": url.strip()})


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
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                resp = await client.post(f"{API_BASE}/api/v1/process/audio", files=files)
                return resp.json()
    except httpx.ConnectError:
        return {"error": f"无法连接到 AVC API 服务 ({API_BASE})，请确认 api.py 已启动"}
    except Exception as e:
        return {"error": f"上传失败: {e}"}


@mcp.tool()
async def process_batch(urls: list[str]) -> dict:
    """批量处理多个B站视频链接，返回 task_id"""
    if not urls:
        return {"error": "URL 列表不能为空"}
    clean_urls = [u.strip() for u in urls if u.strip()]
    if not clean_urls:
        return {"error": "没有有效的 URL"}
    return await _api("POST", "/api/v1/process/batch", json={"urls": clean_urls})


@mcp.tool()
async def get_task_status(task_id: str) -> dict:
    """查询任务状态和结果"""
    return await _api("GET", f"/api/v1/task/{task_id}")


@mcp.tool()
async def cancel_task(task_id: str) -> dict:
    """取消正在处理的任务"""
    return await _api("POST", f"/api/v1/task/{task_id}/cancel")


@mcp.tool()
async def analyze_video(url: str) -> dict:
    """分析B站视频：一键完成转写+LLM结构化分析，返回 title/summary/key_points/segments"""
    if not url.strip():
        return {"error": "URL 不能为空"}
    return await _api("POST", "/api/v1/analyze/video", data={"video_url": url.strip()})


@mcp.tool()
async def generate_mindmap(task_id: str) -> dict:
    """为已完成的任务生成思维导图，返回 Mermaid + JSON 文件路径"""
    task = await _api("GET", f"/api/v1/task/{task_id}")
    if "error" in task:
        return task
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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
