"""MCP Server — 薄适配层，将 MCP Tool 调用转发到本地 FastAPI 服务"""

import asyncio
import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

from src.mcp.bilibili_api import search_videos
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
async def process_bilibili(
    url: str,
    summarize: bool = False,
    disable_llm_polish: bool = False,
    disable_llm_summary: bool = False,
    output_style: str = "",
    prompt_hint: str = "",
) -> dict:
    """处理B站视频链接，返回 task_id 用于查询状态"""
    if not url.strip():
        return {"error": "URL 不能为空"}
    body: dict = {"video_url": url.strip()}
    if summarize:
        body["summarize"] = True
    if disable_llm_polish:
        body["disable_llm_polish"] = True
    if disable_llm_summary:
        body["disable_llm_summary"] = True
    if output_style:
        body["output_style"] = output_style
    if prompt_hint:
        body["prompt_hint"] = prompt_hint
    return await _api("POST", "/api/v1/process/bilibili", json=body)


@mcp.tool()
async def process_audio(
    file_path: str,
    summarize: bool = False,
    disable_llm_polish: bool = False,
    disable_llm_summary: bool = False,
    output_style: str = "",
    prompt_hint: str = "",
) -> dict:
    """处理本地音频/视频文件，返回 task_id"""
    if not file_path.strip():
        return {"error": "文件路径不能为空"}
    file_path = file_path.strip()
    if not os.path.isfile(file_path):
        return {"error": f"文件不存在: {file_path}"}
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".webm",
        ".flv",
    ):
        return {"error": f"不支持的文件格式: {ext}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            with open(file_path, "rb") as f:
                data: dict = {}
                if summarize:
                    data["summarize"] = "true"
                if disable_llm_polish:
                    data["disable_llm_polish"] = "true"
                if disable_llm_summary:
                    data["disable_llm_summary"] = "true"
                if output_style:
                    data["output_style"] = output_style
                if prompt_hint:
                    data["prompt_hint"] = prompt_hint
                files = {"file": (os.path.basename(file_path), f)}
                resp = await client.post(f"{API_BASE}/api/v1/process/audio", files=files, data=data)
                return resp.json()
    except httpx.ConnectError:
        return {"error": f"无法连接到 AVC API 服务 ({API_BASE})，请确认 api.py 已启动"}
    except Exception as e:
        return {"error": f"上传失败: {e}"}


@mcp.tool()
async def process_batch(
    urls: list[str],
    summarize: bool = False,
    disable_llm_polish: bool = False,
    disable_llm_summary: bool = False,
    output_style: str = "",
    prompt_hint: str = "",
) -> dict:
    """批量处理多个B站视频链接，返回 task_id"""
    if not urls:
        return {"error": "URL 列表不能为空"}
    clean_urls = [u.strip() for u in urls if u.strip()]
    if not clean_urls:
        return {"error": "没有有效的 URL"}
    body: dict = {"urls": clean_urls}
    if summarize:
        body["summarize"] = True
    if disable_llm_polish:
        body["disable_llm_polish"] = True
    if disable_llm_summary:
        body["disable_llm_summary"] = True
    if output_style:
        body["output_style"] = output_style
    if prompt_hint:
        body["prompt_hint"] = prompt_hint
    return await _api("POST", "/api/v1/process/batch", json=body)


@mcp.tool()
async def get_task_status(task_id: str) -> dict:
    """查询任务状态和结果（含文本内容，Agent 无需下载文件）"""
    task = await _api("GET", f"/api/v1/task/{task_id}")
    if "error" in task:
        return task
    result = task.get("result", {})
    text = {}
    for src, dst in [
        ("polished_text", "polished_text"),
        ("transcript", "transcript"),
        ("audio_text", "transcript"),
        ("summary", "summary"),
        ("summary_text", "summary"),
    ]:
        if result.get(src):
            text[dst] = result[src]
    if result.get("key_points"):
        text["key_points"] = result["key_points"]
    return {
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "message": task.get("message", ""),
        "text": text if text else None,
        "output_dir": result.get("output_dir", ""),
    }


@mcp.tool()
async def cancel_task(task_id: str) -> dict:
    """取消正在处理的任务"""
    return await _api("POST", f"/api/v1/task/{task_id}/cancel")


@mcp.tool()
async def analyze_video(url: str, prompt_hint: str = "") -> dict:
    """分析B站视频：一键完成转写+LLM结构化分析，返回 title/summary/key_points/segments"""
    if not url.strip():
        return {"error": "URL 不能为空"}
    data: dict = {"video_url": url.strip()}
    if prompt_hint:
        data["prompt_hint"] = prompt_hint
    return await _api("POST", "/api/v1/analyze/video", data=data)


@mcp.tool()
async def search_bilibili(keyword: str, max_results: int = 10) -> dict:
    """搜索B站视频，返回匹配视频的 bvid/title/duration/play_count/description/author/url 列表"""
    return await search_videos(keyword=keyword, max_results=max_results)


@mcp.tool()
async def generate_mindmap(task_id: str, prompt_hint: str = "") -> dict:
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
    from src.services.mindmap import export_mindmap_to_files, render_mermaid
    from src.services.mindmap import generate_mindmap as _gen

    output_dir = result.get("output_dir", f"./out/{task_id}")
    output = await _gen(text=text, title=title, prompt_hint=prompt_hint)
    files = export_mindmap_to_files(output, output_dir)
    return {
        "task_id": task_id,
        "title": title,
        "node_count": output.node_count,
        "mermaid": render_mermaid(output.root),
        "structure": output.root.model_dump(),
        "files": files,
    }


# ============================================================
# Resources — Agent 按 URI 直接读取内容，无需下载文件
# ============================================================


def _get_completed_task(task_id: str) -> dict | None:
    """获取已完成的任务数据，未完成或不存在返回 None"""
    task = asyncio.run(_api("GET", f"/api/v1/task/{task_id}"))
    if "error" in task or task.get("status") != "completed":
        return None
    return task.get("result", {})


@mcp.resource("avc://task/{task_id}/transcript")
async def get_transcript(task_id: str) -> str:
    """原始转写全文"""
    result = _get_completed_task(task_id)
    if not result:
        return "任务未完成或不存在"
    return result.get("transcript") or result.get("audio_text") or "（无转写文本）"


@mcp.resource("avc://task/{task_id}/polished")
async def get_polished(task_id: str) -> str:
    """LLM 润色后文本"""
    result = _get_completed_task(task_id)
    if not result:
        return "任务未完成或不存在"
    return result.get("polished_text") or "（无润色文本）"


@mcp.resource("avc://task/{task_id}/summary")
async def get_summary(task_id: str) -> str:
    """摘要"""
    result = _get_completed_task(task_id)
    if not result:
        return "任务未完成或不存在"
    return result.get("summary") or result.get("summary_text") or "（无摘要）"


@mcp.resource("avc://task/{task_id}/mindmap")
async def get_mindmap_resource(task_id: str) -> str:
    """思维导图 JSON 结构"""
    result = _get_completed_task(task_id)
    if not result:
        return "{}"
    text = result.get("text") or result.get("transcript") or ""
    title = result.get("title") or ""
    if not text:
        return "{}"
    from src.services.mindmap import generate_mindmap as _gen

    output = await _gen(text=text, title=title)
    return output.model_dump_json()


@mcp.resource("avc://task/{task_id}/analysis")
async def get_analysis(task_id: str) -> str:
    """结构化 VideoAnalysis JSON"""
    result = _get_completed_task(task_id)
    if not result:
        return "{}"
    key_points = result.get("key_points", [])
    segments = result.get("segments", [])
    if not key_points and not segments:
        return "{}"
    return json.dumps(
        {"title": result.get("title", ""), "key_points": key_points, "segments": segments},
        ensure_ascii=False,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
