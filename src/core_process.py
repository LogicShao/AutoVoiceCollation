"""
核心处理流程 (向后兼容层)

此文件保留向后兼容性,实际处理逻辑已迁移到 src/core/processors/
所有函数现在都是对应处理器方法的简单包装器
"""

from src.core.processors import AudioProcessor, VideoProcessor, SubtitleProcessor
from src.logger import get_logger

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
    处理音频文件，提取文本并润色 (向后兼容包装器)

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
    批量处理B站视频链接 (向后兼容包装器)

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
    生成视频字幕并硬编码到视频（旧接口，保留向后兼容）

    Args:
        video_file: 视频文件路径

    Returns:
        Tuple[str, str]: (字幕文件路径, 输出视频路径)
    """
    return _subtitle_processor.process_simple(video_file)


def generate_subtitles_advanced(
    media_file: str,
    file_type: str = "srt",
    model: str = "paraformer",
    segmenter_type: str = "pause",
    output_type: str = "subtitle_only",
    api_server: str = None,
    pause_threshold: float = 0.6,
    max_chars: int = 16,
    batch_size_s: int = 5,
    paraformer_chunk_size_s: int = 30,
    task_id: str = None,
):
    """
    增强版字幕生成函数（向后兼容包装器）

    Args:
        media_file: 媒体文件路径（音频或视频）
        file_type: 字幕格式 ('srt' 或 'cc')
        model: ASR 模型 ('paraformer' 或 'sense_voice')
        segmenter_type: 分段策略 ('pause' 或 'llm')
        output_type: 输出类型
        api_server: LLM API 服务器
        pause_threshold: 停顿阈值（秒）
        max_chars: 每段最大字符数
        batch_size_s: SenseVoice 批处理大小（秒）
        paraformer_chunk_size_s: Paraformer 分块大小（秒）
        task_id: 任务ID

    Returns:
        Tuple: (字幕文件路径, 带字幕视频路径或None, 处理信息)
    """
    return _subtitle_processor.process(
        media_file=media_file,
        file_type=file_type,
        model=model,
        segmenter_type=segmenter_type,
        output_type=output_type,
        api_server=api_server,
        pause_threshold=pause_threshold,
        max_chars=max_chars,
        batch_size_s=batch_size_s,
        paraformer_chunk_size_s=paraformer_chunk_size_s,
        task_id=task_id,
    )


def upload_audio(
    audio_path,
    llm_api,
    temperature,
    max_tokens,
    text_only: bool = False,
    task_id: str = None,
):
    """
    上传并处理音频文件 (向后兼容包装器)

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
    下载并处理B站视频 (向后兼容包装器)

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
