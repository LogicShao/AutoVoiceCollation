"""
核心处理流程

提供向后兼容的处理函数，实际逻辑已迁移到 src/core/processors/
"""

from src.core.processors import AudioProcessor, VideoProcessor, SubtitleProcessor
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

# 实例化处理器
_audio_processor = AudioProcessor()
_video_processor = VideoProcessor()
_subtitle_processor = SubtitleProcessor()


def process_audio(
    audio_file,
    llm_api: str,
    temperature: float,
    max_tokens: int,
    text_only: bool = False,
    task_id: str = None,
):
    """
    处理音频文件，提取文本并润色

    Args:
        audio_file: 音频文件对象
        llm_api: LLM API服务
        temperature: 温度参数
        max_tokens: 最大token数
        text_only: 是否只返回纯文本结果
        task_id: 任务ID

    Returns:
        Tuple: (结果数据, 提取时间, 润色时间, ZIP文件路径)
    """
    return _audio_processor.process(
        audio_file, llm_api, temperature, max_tokens, text_only, task_id
    )


def process_multiple_urls(
    urls: str,
    llm_api: str,
    temperature: float,
    max_tokens: int,
    text_only: bool = False,
    task_id: str = None,
):
    """
    批量处理B站视频链接

    Args:
        urls: 多个URL，用换行符分隔
        llm_api: LLM API服务
        temperature: 温度参数
        max_tokens: 最大token数
        text_only: 是否只返回纯文本结果
        task_id: 任务ID

    Returns:
        Tuple: (输出目录列表, 总提取时间, 总润色时间, None, None, None)
    """
    result_str, extract_time, polish_time, _ = _video_processor.process_batch(
        urls, llm_api, temperature, max_tokens, text_only, task_id
    )
    return result_str, extract_time, polish_time, None, None, None


def process_subtitles(video_file: str):
    """
    生成视频字幕并硬编码到视频

    Args:
        video_file: 视频文件路径

    Returns:
        Tuple[str, str]: (字幕文件路径, 输出视频路径)
    """
    return _subtitle_processor.process_simple(video_file)


def upload_audio(
    audio_path,
    llm_api,
    temperature,
    max_tokens,
    text_only: bool = False,
    task_id: str = None,
):
    """
    上传并处理音频文件

    Args:
        audio_path: 音频文件路径
        llm_api: LLM API服务
        temperature: 温度参数
        max_tokens: 最大token数
        text_only: 是否只返回纯文本结果
        task_id: 任务ID

    Returns:
        Tuple: 处理结果
    """
    if audio_path is None:
        return "请上传一个音频文件。", None, None, None, None, None

    return _audio_processor.process_uploaded_audio(
        audio_path, llm_api, temperature, max_tokens, text_only, task_id
    )


def bilibili_video_download_process(
    video_url,
    llm_api,
    temperature,
    max_tokens,
    text_only: bool = False,
    task_id: str = None,
):
    """
    下载并处理B站视频

    Args:
        video_url: B站视频URL
        llm_api: LLM API服务
        temperature: 温度参数
        max_tokens: 最大token数
        text_only: 是否只返回纯文本结果
        task_id: 任务ID

    Returns:
        Tuple: (结果数据, 总提取时间, 润色时间, ZIP文件路径)
    """
    return _video_processor.process(
        video_url, llm_api, temperature, max_tokens, text_only, task_id
    )
