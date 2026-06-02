"""B站 CC 字幕探测、下载和文本提取模块

提供 CC 字幕快速通道，跳过冗余 ASR 处理。
"""

import asyncio
import concurrent.futures
import contextlib
import re

import httpx

from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

_BILIBILI_API = "https://api.bilibili.com"
_BILIBILI_URL = "https://www.bilibili.com/"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Session-level cache (module lifecycle)
_http: httpx.AsyncClient | None = None


async def _ensure_session() -> httpx.AsyncClient:
    """懒初始化共享 HTTP 会话"""
    global _http
    if _http is None:
        _http = httpx.AsyncClient(
            cookies=httpx.Cookies(),
            timeout=httpx.Timeout(15),
            headers={"User-Agent": _UA, "Referer": _BILIBILI_URL},
            follow_redirects=True,
        )
        with contextlib.suppress(Exception):
            await _http.get(_BILIBILI_URL)
    return _http


async def fetch_cc_subtitle_list(bvid: str, cid: str) -> list[dict]:
    """
    获取 B站视频 CC 字幕列表

    Args:
        bvid: B站视频 BV 号
        cid: 视频 cid

    Returns:
        字幕列表，每项包含 lang_key、subtitle_url 等字段
    """
    try:
        http = await _ensure_session()
        url = f"{_BILIBILI_API}/x/player/v2"
        resp = await http.get(url, params={"bvid": bvid, "cid": cid})
        resp.raise_for_status()
        data = resp.json()
        player_data = data.get("data") or {}
        subtitle_data = player_data.get("subtitle") or {}
        subtitles = subtitle_data.get("subtitles", [])
        return subtitles if isinstance(subtitles, list) else []
    except Exception as e:
        logger.warning(f"[CC] fetch_cc_subtitle_list failed for {bvid}/{cid}: {e}")
        return []


async def download_cc_subtitle(subtitle_url: str) -> dict:
    """
    下载 B站 CC 字幕 JSON

    Args:
        subtitle_url: 字幕 URL（可能以 // 开头）

    Returns:
        字幕 JSON 数据
    """
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url

    try:
        http = await _ensure_session()
        resp = await http.get(subtitle_url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"[CC] download_cc_subtitle failed for {subtitle_url}: {e}")
        return {}


def extract_cc_text(subtitle_json: dict) -> str:
    """
    从 B站 CC 字幕 JSON 提取纯文本

    Args:
        subtitle_json: 字幕 JSON 数据（含 body[] 字段）

    Returns:
        拼接后的纯文本
    """
    body = subtitle_json.get("body", [])
    if not body:
        return ""
    return " ".join(item.get("content", "") for item in body if item.get("content"))


async def has_usable_cc(bvid: str, cid: str) -> str | None:
    """
    检测视频是否有可用的中文 CC 字幕，并返回文本

    判断条件：
    - 字幕语言为中文（lang_key 为 "zh" 或 "zh-cn"，大小写不敏感）
    - 提取文本长度 >= 200 字符

    Args:
        bvid: B站视频 BV 号
        cid: 视频 cid

    Returns:
        CC 字幕文本（如果可用），否则返回 None
    """
    try:
        subtitles = await fetch_cc_subtitle_list(bvid, cid)
        if not subtitles:
            logger.debug(f"[CC] no subtitles found for {bvid}/{cid}")
            return None

        # 筛选中文字幕
        chinese_subtitles = []
        for subtitle in subtitles:
            lang_key = str(subtitle.get("lang_key", "")).lower()
            if lang_key in {"zh", "zh-cn"}:
                chinese_subtitles.append(subtitle)

        if not chinese_subtitles:
            logger.debug(f"[CC] no Chinese subtitles for {bvid}/{cid}")
            return None

        # 尝试每个中文字幕，取第一个有效的
        for subtitle in chinese_subtitles:
            subtitle_url = subtitle.get("subtitle_url", "")
            if not subtitle_url:
                continue

            subtitle_json = await download_cc_subtitle(subtitle_url)
            if not subtitle_json:
                continue

            text = extract_cc_text(subtitle_json)
            if len(text) >= 200:
                logger.info(f"[CC] usable CC found for {bvid}/{cid}, length={len(text)}")
                return text
            logger.debug(f"[CC] CC text too short ({len(text)} chars) for {bvid}/{cid}")

        return None

    except Exception as e:
        logger.warning(f"[CC] has_usable_cc failed for {bvid}/{cid}: {e}")
        return None


def _run_async_in_thread(coro) -> str | None:
    """
    在独立线程中运行异步协程，避免与当前事件循环冲突。

    用于从同步处理器代码中调用异步 CC 检测函数。
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        try:
            return future.result(timeout=20)
        except Exception as e:
            logger.warning(f"[CC] async execution failed: {e}")
            return None


def check_cc_sync(bvid: str, cid: str) -> str | None:
    """
    同步接口：检测并返回 CC 字幕文本（供同步处理器调用）

    Args:
        bvid: B站视频 BV 号
        cid: 视频 cid（字符串或整数均可）

    Returns:
        CC 字幕文本（如果可用），否则返回 None
    """
    return _run_async_in_thread(has_usable_cc(bvid, str(cid)))


def extract_bvid_from_url(url: str) -> str | None:
    """从 B站 URL 中提取 BV 号"""
    match = re.search(r"(BV\w+)", url)
    return match.group(1) if match else None


async def get_cid_from_bvid(bvid: str) -> str | None:
    """
    通过 bvid 获取第一个分P的 cid

    Args:
        bvid: B站视频 BV 号

    Returns:
        cid 字符串，失败返回 None
    """
    try:
        http = await _ensure_session()
        url = f"{_BILIBILI_API}/x/web-interface/view"
        resp = await http.get(url, params={"bvid": bvid})
        resp.raise_for_status()
        data = resp.json()
        cid = data.get("data", {}).get("cid")
        return str(cid) if cid else None
    except Exception as e:
        logger.warning(f"[CC] get_cid_from_bvid failed for {bvid}: {e}")
        return None


def get_cid_sync(bvid: str) -> str | None:
    """同步接口：获取 bvid 对应的 cid"""
    return _run_async_in_thread(get_cid_from_bvid(bvid))
