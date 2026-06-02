"""B站公开搜索 API — WBI 签名 + 视频搜索（无需登录）"""

import contextlib
import hashlib
import re
import time
import urllib.parse
from functools import reduce

import httpx
from pydantic import BaseModel, Field

from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

_SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"
_NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
_BILIBILI_URL = "https://www.bilibili.com/"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_MIXIN_KEY_ENC_TAB = [
    46,
    47,
    18,
    2,
    53,
    8,
    23,
    32,
    15,
    50,
    10,
    31,
    58,
    3,
    45,
    35,
    27,
    43,
    5,
    49,
    33,
    9,
    42,
    19,
    29,
    28,
    14,
    39,
    12,
    38,
    41,
    13,
    37,
    48,
    7,
    16,
    24,
    55,
    40,
    61,
    26,
    17,
    0,
    1,
    60,
    51,
    30,
    4,
    22,
    25,
    54,
    21,
    56,
    59,
    6,
    63,
    57,
    62,
    11,
    36,
    20,
    34,
    44,
    52,
]

# Session-level cache（MCP 进程生命周期内复用）
_http: httpx.AsyncClient | None = None
_wbi_keys: tuple[float, str, str] | None = None


async def _ensure_session() -> httpx.AsyncClient:
    """懒初始化共享 HTTP 会话（首次自动获取 buvid3 cookie）"""
    global _http
    if _http is None:
        _http = httpx.AsyncClient(
            cookies=httpx.Cookies(),
            timeout=httpx.Timeout(15),
            headers={"User-Agent": _UA, "Referer": _BILIBILI_URL},
            follow_redirects=True,
        )
        # 获取 buvid3 cookie 容错：homepage 挂了也不影响后续搜索
        with contextlib.suppress(Exception):
            await _http.get(_BILIBILI_URL)
    return _http


async def _get_wbi_keys() -> tuple[str, str]:
    """获取 WBI 签名密钥（缓存 1 小时）"""
    global _wbi_keys
    now = time.time()
    if _wbi_keys and now - _wbi_keys[0] < 3600:
        return _wbi_keys[1], _wbi_keys[2]

    http = await _ensure_session()
    resp = await http.get(_NAV_URL)
    resp.raise_for_status()
    data = resp.json()
    wbi_img = data.get("data", {}).get("wbi_img", {})
    img_url = wbi_img.get("img_url", "")
    sub_url = wbi_img.get("sub_url", "")
    if not img_url or not sub_url:
        raise RuntimeError("无法获取 WBI 签名密钥（nav 接口返回异常）")

    img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
    sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
    _wbi_keys = (now, img_key, sub_key)
    return img_key, sub_key


def _sign_params(params: dict, img_key: str, sub_key: str) -> dict:
    """WBI 签名：向 params 添加 wts 和 w_rid"""
    mixin = reduce(lambda s, i: s + (img_key + sub_key)[i], _MIXIN_KEY_ENC_TAB, "")[:32]

    signed = dict(params)
    signed["wts"] = int(time.time())

    signed = dict(sorted(signed.items()))
    filtered = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in signed.items()}
    query = urllib.parse.urlencode(filtered)
    signed["w_rid"] = hashlib.md5((query + mixin).encode()).hexdigest()
    return signed


async def search_videos(keyword: str, max_results: int = 10) -> dict:
    """搜索 B 站视频

    Args:
        keyword: 搜索关键词
        max_results: 最大返回数量 (1-50)

    Returns:
        {"results": [{bvid, title, duration, play_count, description, author, url}], "total": int}
        出错时返回 {"error": "..."}
    """
    keyword = keyword.strip()
    if not keyword:
        return {"error": "搜索关键词不能为空"}
    max_results = max(1, min(max_results, 50))

    try:
        img_key, sub_key = await _get_wbi_keys()
        signed = _sign_params(
            {"search_type": "video", "keyword": keyword, "page": "1"},
            img_key,
            sub_key,
        )

        http = await _ensure_session()
        resp = await http.get(_SEARCH_URL, params=signed)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            return {
                "error": f"搜索失败(code={data.get('code')}): {data.get('message', '未知错误')}"
            }

        items = data.get("data", {}).get("result", [])
        results: list[dict] = []
        for item in items:
            if item.get("type") != "video":
                continue
            if len(results) >= max_results:
                break

            title_raw = item.get("title", "")
            title_clean = re.sub(r"<[^>]+>", "", title_raw)

            results.append(
                {
                    "bvid": item.get("bvid", ""),
                    "title": title_clean,
                    "duration": item.get("duration", ""),
                    "play_count": item.get("play", 0),
                    "description": item.get("description", ""),
                    "author": item.get("author", ""),
                    "url": f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                }
            )

        return {
            "keyword": keyword,
            "total": data.get("data", {}).get("numResults", len(results)),
            "results": results,
        }

    except httpx.ConnectError:
        return {"error": "无法连接到 B 站搜索接口，请检查网络"}
    except httpx.HTTPStatusError as e:
        return {"error": f"B 站接口返回 HTTP {e.response.status_code}"}
    except Exception as e:
        return {"error": f"搜索异常: {e}"}


# ========== 视频元数据 ==========


class VideoMetadata(BaseModel):
    """B站视频元数据"""

    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    owner: str = ""
    chapters: list[dict] = Field(default_factory=list)
    hot_comments: list[str] = Field(default_factory=list)


async def get_video_metadata(bvid: str) -> VideoMetadata:
    """聚合 B站视频元数据（3 个 API），单 API 失败则字段置空"""
    result = VideoMetadata()

    try:
        http = await _ensure_session()
        resp = await http.get(
            "https://api.bilibili.com/x/web-interface/view", params={"bvid": bvid}
        )
        resp.raise_for_status()
        data = resp.json().get("data", {}) or {}
        result.title = data.get("title", "")
        result.description = (data.get("desc", "") or "")[:1000]
        result.tags = [t.get("tag_name", "") for t in data.get("tags", []) if isinstance(t, dict)]
        result.owner = data.get("owner", {}).get("name", "")
    except Exception as e:
        logger.debug(f"[Metadata] view API failed for {bvid}: {e}")

    try:
        http = await _ensure_session()
        resp = await http.get("https://api.bilibili.com/x/player/pagelist", params={"bvid": bvid})
        resp.raise_for_status()
        entries = resp.json().get("data", []) or []
        result.chapters = [
            {"title": e.get("part", ""), "part_number": i + 1, "duration": e.get("duration", 0)}
            for i, e in enumerate(entries)
            if isinstance(e, dict)
        ]
    except Exception as e:
        logger.debug(f"[Metadata] pagelist API failed for {bvid}: {e}")

    try:
        http = await _ensure_session()
        resp = await http.get(
            "https://api.bilibili.com/x/v2/reply/main", params={"oid": bvid, "type": 1}
        )
        resp.raise_for_status()
        replies = resp.json().get("data", {}).get("replies", []) or []
        result.hot_comments = [
            (
                r.get("content", {}).get("message", "")
                if isinstance(r.get("content"), dict)
                else r.get("content", "")
            )[:100]
            for r in replies[:5]
            if r
        ]
    except Exception as e:
        logger.debug(f"[Metadata] reply API failed for {bvid}: {e}")

    return result


def _truncate_to_token_budget(text: str, max_tokens: int = 500) -> str:
    """按 token 预算截断文本（汉字≈1 token，英文≈0.25 token/char）"""
    if not text:
        return ""
    estimated = 0
    result: list[str] = []
    for char in text:
        token_est = 1 if ord(char) > 127 else 0.25
        if estimated + token_est > max_tokens:
            break
        estimated += token_est
        result.append(char)
    return "".join(result)


def format_metadata_for_prompt(metadata: VideoMetadata) -> str:
    """将 VideoMetadata 格式化为 LLM prompt 注入文本，限制 500 tokens"""
    lines = ["[视频元数据]"]
    if metadata.title:
        lines.append(f"标题: {metadata.title}")
    if metadata.description:
        lines.append(f"描述: {metadata.description[:200]}")
    if metadata.tags:
        lines.append(f"标签: {', '.join(metadata.tags)}")
    if metadata.owner:
        lines.append(f"UP主: {metadata.owner}")
    if metadata.chapters:
        chapters_str = "; ".join(
            f"P{c.get('part_number', '?')}:{c.get('title', '')}" for c in metadata.chapters
        )
        lines.append(f"分P目录: {chapters_str}")
    if metadata.hot_comments:
        lines.append(f"热门评论: {' | '.join(metadata.hot_comments)}")

    full = "\n".join(lines)
    return _truncate_to_token_budget(full, 500)
