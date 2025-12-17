"""
核心处理流程的辅助工具函数
"""

from typing import Optional, Dict, Any

from src.logger import get_logger
from src.process_history import get_history_manager, ProcessRecord

logger = get_logger(__name__)
history_manager = get_history_manager()


def check_bilibili_processed(video_url: str) -> Optional[ProcessRecord]:
    """
    检查B站视频是否已被处理过

    Args:
        video_url: B站视频URL

    Returns:
        ProcessRecord: 如果已处理过，返回处理记录；否则返回None
    """
    identifier = history_manager.extract_bilibili_id(video_url)
    if not identifier:
        logger.warning(f"无法从URL提取视频ID: {video_url}")
        return None

    if history_manager.check_processed(identifier):
        record = history_manager.get_record(identifier)
        logger.info(
            f"检测到已处理过的视频: {identifier}, 上次处理时间: {record.last_processed}"
        )
        return record

    return None


def record_bilibili_process(
    video_url: str,
    title: str,
    output_dir: str,
    config: Dict[str, Any],
    outputs: Dict[str, str],
) -> ProcessRecord:
    """
    记录B站视频处理历史

    Args:
        video_url: B站视频URL
        title: 视频标题
        output_dir: 输出目录
        config: 处理配置（ASR模型、LLM配置等）
        outputs: 输出文件路径字典

    Returns:
        ProcessRecord: 创建的处理记录
    """
    try:
        record = history_manager.create_record_from_bilibili(
            url=video_url,
            title=title,
            output_dir=output_dir,
            config=config,
            outputs=outputs,
        )
        logger.info(f"已记录B站视频处理历史: {record.identifier}")
        return record
    except Exception as e:
        logger.error(f"记录处理历史失败: {e}", exc_info=True)
        return None


def record_local_file_process(
    file_path: str,
    file_type: str,
    title: str,
    output_dir: str,
    config: Dict[str, Any],
    outputs: Dict[str, str],
) -> Optional[ProcessRecord]:
    """
    记录本地文件处理历史

    Args:
        file_path: 本地文件路径
        file_type: 文件类型（local_audio 或 local_video）
        title: 文件标题
        output_dir: 输出目录
        config: 处理配置
        outputs: 输出文件路径字典

    Returns:
        ProcessRecord: 创建的处理记录
    """
    try:
        record = history_manager.create_record_from_local_file(
            file_path=file_path,
            file_type=file_type,
            title=title,
            output_dir=output_dir,
            config=config,
            outputs=outputs,
        )
        logger.info(f"已记录本地文件处理历史: {record.identifier}")
        return record
    except Exception as e:
        logger.error(f"记录处理历史失败: {e}", exc_info=True)
        return None


def build_output_files_dict(output_dir: str, text_only: bool = False) -> Dict[str, str]:
    """
    构建输出文件路径字典

    Args:
        output_dir: 输出目录
        text_only: 是否只有文本输出

    Returns:
        Dict[str, str]: 输出文件路径字典
    """
    import os

    outputs = {
        "audio_transcription": os.path.join(output_dir, "audio_transcription.txt"),
        "polish_text": os.path.join(output_dir, "polish_text.txt"),
    }

    if not text_only:
        outputs.update(
            {
                "summary_text": os.path.join(output_dir, "summary_text.md"),
                "pdf_file": os.path.join(output_dir, "output.pdf"),
                "result_json": os.path.join(output_dir, "result.json"),
            }
        )
    else:
        outputs["result_json"] = os.path.join(output_dir, "result.json")

    # 只保留实际存在的文件
    return {k: v for k, v in outputs.items() if os.path.exists(v)}
