"""B站 CC 字幕探测、下载和文本提取模块

提供 CC 字幕快速通道，跳过冗余 ASR 处理。
"""

import asyncio
import concurrent.futures
import contextlib
import re
import urllib.parse
from typing import Any

import httpx

from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

_BILIBILI_API = "https://api.bilibili.com"
_BILIBILI_URL = "https://www.bilibili.com/"
_MIN_CC_TEXT_LENGTH = 200
_CHINESE_LANG_KEYS = {"zh", "zh-cn", "zh-hans", "zh-hant", "zh-tw", "ai-zh"}
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _new_client() -> httpx.AsyncClient:
    """创建独立 HTTP 会话，避免同步桥复用跨事件循环的 AsyncClient。"""
    return httpx.AsyncClient(
        cookies=httpx.Cookies(),
        timeout=httpx.Timeout(15),
        headers={"User-Agent": _UA, "Referer": _BILIBILI_URL},
        follow_redirects=True,
    )


async def _get_json(url: str, params: dict[str, Any] | None = None) -> dict:
    async with _new_client() as http:
        # 获取 buvid cookie；失败不阻塞主请求，仍允许接口自行返回错误。
        with contextlib.suppress(Exception):
            await http.get(_BILIBILI_URL)

        resp = await http.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}


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
        url = f"{_BILIBILI_API}/x/player/v2"
        data = await _get_json(url, params={"bvid": bvid, "cid": cid})
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
        return await _get_json(subtitle_url)
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
    if not isinstance(body, list):
        return ""
    segments = []
    for item in body:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if content:
            segments.append(content)
    return " ".join(segments)


def _is_chinese_subtitle(subtitle: dict) -> bool:
    lang_key = str(subtitle.get("lang_key", "")).strip().lower()
    if lang_key in _CHINESE_LANG_KEYS or lang_key.startswith("zh"):
        return True

    language = str(subtitle.get("lan_doc") or subtitle.get("language") or "").lower()
    return "中文" in language or "chinese" in language


async def has_usable_cc(bvid: str, cid: str) -> str | None:
    """
    检测视频是否有可用的中文 CC 字幕，并返回文本

    判断条件：
    - 字幕语言为中文
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

        chinese_subtitles = [
            subtitle
            for subtitle in subtitles
            if isinstance(subtitle, dict) and _is_chinese_subtitle(subtitle)
        ]

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
            if len(text) >= _MIN_CC_TEXT_LENGTH:
                logger.info(f"[CC] usable CC found for {bvid}/{cid}, length={len(text)}")
                return text
            logger.debug(f"[CC] CC text too short ({len(text)} chars) for {bvid}/{cid}")

        return None

    except Exception as e:
        logger.warning(f"[CC] has_usable_cc failed for {bvid}/{cid}: {e}")
        return None


def _run_async_in_thread(coro) -> Any:
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
    match = re.search(r"(BV[0-9A-Za-z]+)", url)
    return match.group(1) if match else None


def extract_page_from_url(url: str) -> int:
    """从 B站 URL 中提取分 P 页码，缺省为 1。"""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    raw_page = query.get("p", ["1"])[0]
    with contextlib.suppress(TypeError, ValueError):
        return max(1, int(raw_page))
    return 1


async def get_cid_for_page(bvid: str, page: int = 1) -> str | None:
    """
    通过 bvid 和分 P 页码获取 cid

    Args:
        bvid: B站视频 BV 号
        page: 分 P 页码，从 1 开始

    Returns:
        cid 字符串，失败返回 None
    """
    try:
        page = max(1, int(page))
        url = f"{_BILIBILI_API}/x/player/pagelist"
        data = await _get_json(url, params={"bvid": bvid})
        entries = data.get("data") or []
        if not isinstance(entries, list):
            return None

        fallback_cid = None
        for item in entries:
            if not isinstance(item, dict):
                continue

            cid = item.get("cid")
            if fallback_cid is None and cid:
                fallback_cid = cid

            item_page = item.get("page")
            with contextlib.suppress(TypeError, ValueError):
                if int(item_page) == page and cid:
                    return str(cid)

        cid = fallback_cid if page == 1 else None
        return str(cid) if cid else None
    except Exception as e:
        logger.warning(f"[CC] get_cid_for_page failed for {bvid}/p{page}: {e}")
        return None


async def get_cid_from_bvid(bvid: str) -> str | None:
    """通过 bvid 获取第一个分P的 cid"""
    return await get_cid_for_page(bvid, 1)


def get_cid_for_page_sync(bvid: str, page: int = 1) -> str | None:
    """同步接口：获取 bvid 指定分 P 对应的 cid"""
    return _run_async_in_thread(get_cid_for_page(bvid, page))


def get_cid_sync(bvid: str) -> str | None:
    """同步接口：获取 bvid 对应的 cid"""
    return _run_async_in_thread(get_cid_from_bvid(bvid))
