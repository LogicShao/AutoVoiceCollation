import enum
import glob
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from yt_dlp import YoutubeDL

from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

_pre_text = (
    "本项目使用{ASR_model}+LLM({LLM_api},温度:{temperature})进行音频文本提取和润色，"
    "ASR模型提取的文本可能存在错误和不准确之处，"
    "以及润色之后的文本可能会与原意有所偏差，请仔细辨别。"
)


class FileType(enum.Enum):
    ONLINE = "online"
    LOCAL = "local"


@dataclass
class BiliVideoFile:
    url: str
    path: str
    title: str | None = None
    file_type: FileType = FileType.ONLINE

    def __post_init__(self):
        # 绝对路径
        self.path = os.path.abspath(self.path)
        # 如果没传 title，用文件名
        if not self.title:
            self.title = os.path.splitext(os.path.basename(self.path))[0]

    @property
    def BV_id(self) -> str:
        """从 URL 中提取 BV 号"""
        match = re.search(r"(BV\w+)", self.url)
        return match.group(1) if match else "UnknownBV"

    def __str__(self) -> str:
        return f"{self.title} ({self.url}) -> {self.path}"

    def save_in_json(self, json_file_path):
        data = {
            "url": self.url,
            "path": self.path,
            "title": self.title,
            "file_type": self.file_type.value,
        }
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def save_in_text(
        self,
        polish_text: str,
        llm_api_server: str,
        temperature: float,
        asr_model: str,
        text_file_path: str,
    ):
        pre_text = _pre_text.format(
            ASR_model=asr_model, LLM_api=llm_api_server, temperature=temperature
        )
        pre_text += "\n\n{}".format(self.url)
        with open(text_file_path, "w", encoding="utf-8") as f:
            if self.title:
                f.write(f"{self.title}\n\n")
            f.write(f"{pre_text}\n\n")
            f.write(polish_text)


def new_local_bili_file(path: str, title: str | None = None) -> BiliVideoFile:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"本地文件未找到：{path}")
    abs_path = os.path.abspath(path)
    url = f"file://{abs_path}"
    return BiliVideoFile(url=url, path=abs_path, title=title, file_type=FileType.LOCAL)


def _find_downloaded_file(video_id: str, resolved_dir: str, ext: str) -> Optional[str]:
    """
    在 resolved_dir 中查找以 video_id 开头并以 ext 结尾的文件（支持 _pN 等后缀）。
    返回最匹配（最近修改时间）的文件绝对路径或 None。
    """
    pattern = os.path.join(resolved_dir, f"{video_id}*.{ext}")
    candidates = glob.glob(pattern)
    if not candidates:
        return None
    # 按修改时间降序，优先最新的（通常是我们刚生成的）
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return os.path.abspath(candidates[0])


# ========== 下载视频 ==========
def download_bilibili_video(
    video_url,
    output_format="mp4",
    output_dir: str | None = None,
    retries: int = 3,
    delay: float = 3.0,
) -> BiliVideoFile:
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"尝试第 {attempt} 次下载视频：{video_url}")
            return _download_bilibili_video_once(video_url, output_format, output_dir)
        except Exception as e:
            logger.warning(f"下载失败（第 {attempt} 次），错误信息：{e}")
            time.sleep(delay)
    raise RuntimeError("视频下载失败，已达最大重试次数。")


def _download_bilibili_video_once(
    video_url, output_format="mp4", output_dir: str | None = None
) -> BiliVideoFile:
    output_file_path = {"path": None}

    resolved_dir = os.path.abspath(os.getcwd() if output_dir is None else output_dir)
    os.makedirs(resolved_dir, exist_ok=True)
    output_template = os.path.join(resolved_dir, "%(id)s.%(ext)s")

    with YoutubeDL({"quiet": True}) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)

    video_id = info_dict.get("id")
    title = info_dict.get("title")

    existing = _find_downloaded_file(video_id, resolved_dir, output_format)
    if existing and os.path.isfile(existing):
        logger.info(f"已检测到本地缓存文件：{existing}，跳过下载。")
        return BiliVideoFile(url=video_url, path=existing, title=title)

    def hook(d):
        if d.get("status") == "finished" and "filename" in d:
            output_file_path["path"] = d["filename"]

    ydl_opts = {
        "format": "bv+ba/best",
        "outtmpl": output_template,
        "progress_hooks": [hook],
        "noplaylist": True,
        "quiet": False,
        "restrictfilenames": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    found = _find_downloaded_file(video_id, resolved_dir, output_format)
    if found:
        logger.info(f"下载成功，文件路径：{found}")
        return BiliVideoFile(url=video_url, path=found, title=title)

    if output_file_path["path"]:
        base_no_ext = os.path.splitext(os.path.basename(output_file_path["path"]))[0]
        candidate = os.path.join(resolved_dir, base_no_ext + f".{output_format}")
        if os.path.isfile(candidate):
            return BiliVideoFile(url=video_url, path=candidate, title=title)

    raise RuntimeError("未能捕获输出文件路径，请检查下载流程。")


# ========== 下载音频 ==========
def download_bilibili_audio(
    video_url,
    output_format="mp3",
    output_dir: str | None = None,
    retries: int = 3,
    delay: float = 3.0,
) -> BiliVideoFile:
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"尝试第 {attempt} 次下载：{video_url}")
            return _download_bilibili_audio_once(video_url, output_format, output_dir)
        except Exception as e:
            logger.warning(f"下载失败（第 {attempt} 次），错误信息：{e}")
            time.sleep(delay)
    raise RuntimeError("音频下载失败，已达最大重试次数。")


def _download_bilibili_audio_once(
    video_url, output_format="mp3", output_dir: str | None = None
) -> BiliVideoFile:
    output_file_path = {"path": None}

    resolved_dir = os.path.abspath(os.getcwd() if output_dir is None else output_dir)
    os.makedirs(resolved_dir, exist_ok=True)
    output_template = os.path.join(resolved_dir, "%(id)s.%(ext)s")

    with YoutubeDL({"quiet": True}) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)

    video_id = info_dict.get("id")
    title = info_dict.get("title")

    existing = _find_downloaded_file(video_id, resolved_dir, output_format)
    if existing and os.path.isfile(existing):
        logger.info(f"音频文件已存在：{existing}，跳过下载。")
        return BiliVideoFile(url=video_url, path=existing, title=title)

    def hook(d):
        if d.get("status") == "finished" and "filename" in d:
            output_file_path["path"] = d["filename"]

    ydl_opts = {
        "format": "ba",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": output_format,
                "preferredquality": "192",
            }
        ],
        "progress_hooks": [hook],
        "noplaylist": True,
        "quiet": False,
        "restrictfilenames": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    found = _find_downloaded_file(video_id, resolved_dir, output_format)
    if found:
        logger.info(f"音频下载并转换成功：{found}")
        return BiliVideoFile(url=video_url, path=found, title=title)

    if output_file_path["path"]:
        base_no_ext = os.path.splitext(os.path.basename(output_file_path["path"]))[0]
        candidate = os.path.join(resolved_dir, base_no_ext + f".{output_format}")
        if os.path.isfile(candidate):
            return BiliVideoFile(url=video_url, path=candidate, title=title)

    raise RuntimeError("未能捕获输出文件路径，请检查下载流程。")


def extract_audio_from_video(
    video_path: str, output_format: str = "mp3", output_dir: str | None = None
) -> str:
    """
    从视频中提取音频并保存为指定格式。

    :param video_path: 视频文件路径
    :param output_format: 输出音频格式（如 'mp3', 'wav'）
    :param output_dir: 音频输出目录，默认为视频同目录
    :return: 提取后的音频文件路径
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"视频文件未找到：{video_path}")

    # 设置输出目录和文件名
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = output_dir or os.path.dirname(video_path)
    os.makedirs(output_dir, exist_ok=True)

    audio_path = os.path.join(output_dir, f"{base_name}.{output_format}")

    # 构造 ffmpeg 命令
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-vn",  # 不导出视频
        "-acodec",
        "libmp3lame" if output_format == "mp3" else "pcm_s16le",
        "-y",  # 覆盖已存在文件
        audio_path,
    ]

    logger.info(f"开始提取音频：{audio_path}")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败：{result.stderr}")

    return audio_path


# ========== 多P视频支持 ==========

@dataclass
class BiliVideoPart:
    """B站视频分P信息"""
    part_number: int
    title: str
    video_id: str
    url: str
    duration: int = 0
    thumbnail: Optional[str] = None


@dataclass
class BiliMultiPartVideo:
    """B站多P视频信息"""
    main_url: str
    main_title: str
    total_parts: int
    parts: list["BiliVideoPart"]

    def get_selected_parts(self, part_numbers: list[int]) -> list["BiliVideoPart"]:
        """根据分P编号获取选中的分P"""
        return [p for p in self.parts if p.part_number in part_numbers]


def detect_multi_part(video_url: str) -> tuple[bool, Optional[dict]]:
    """
    检测视频是否为多P

    :param video_url: B站视频URL
    :return: (是否为多P, 视频信息字典)
    """
    logger.info(f"检测多P视频：{video_url}")
    try:
        # 关键：noplaylist: False 启用播放列表模式
        with YoutubeDL({"quiet": True, "noplaylist": False}) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)

        # 必须检查 entries 长度 > 1，因为某些单P视频也可能返回 playlist 类型
        is_multipart = (
            "_type" in info_dict
            and info_dict["_type"] == "playlist"
            and len(info_dict.get("entries", [])) > 1
        )

        logger.info(f"多P检测结果：{is_multipart}, 分P数量：{len(info_dict.get('entries', []))}")
        return is_multipart, info_dict if is_multipart else None

    except Exception as e:
        logger.error(f"多P检测失败：{e}", exc_info=True)
        return False, None


def get_multi_part_info(video_url: str) -> Optional[BiliMultiPartVideo]:
    """
    获取多P视频信息

    :param video_url: B站视频URL
    :return: 多P视频信息对象，如果不是多P则返回None
    """
    is_multipart, info_dict = detect_multi_part(video_url)

    if not is_multipart or not info_dict:
        return None

    entries = info_dict.get("entries", [])
    parts = []

    for idx, entry in enumerate(entries, start=1):
        if not entry:  # 跳过无效的 entry
            continue

        parts.append(
            BiliVideoPart(
                part_number=idx,
                title=entry.get("title", f"第{idx}P"),
                video_id=entry.get("id", ""),
                url=entry.get("webpage_url") or entry.get("url", ""),
                duration=entry.get("duration", 0),
                thumbnail=entry.get("thumbnail"),
            )
        )

    multi_part_info = BiliMultiPartVideo(
        main_url=video_url,
        main_title=info_dict.get("title", "未知视频"),
        total_parts=len(parts),
        parts=parts,
    )

    logger.info(f"多P视频信息：{multi_part_info.main_title}, 共 {multi_part_info.total_parts} P")
    return multi_part_info
