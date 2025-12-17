"""
音频文本提取 (向后兼容层)

此文件保留向后兼容性,实际ASR逻辑已迁移到 src/services/asr/
"""

from typing import Optional

from src.services.asr import get_asr_service, transcribe_audio
from src.utils.logging.logger import get_logger, configure_third_party_loggers
from src.utils.config import get_config

logger = get_logger(__name__)

# 标记是否已配置日志
_log_configured = False


def _ensure_log_configured():
    """确保第三方日志已配置（仅执行一次）"""
    global _log_configured
    if not _log_configured:
        config = get_config()
        configure_third_party_loggers(config.third_party_log_level)
        _log_configured = True


def get_sense_voice_model():
    """
    获取SenseVoice模型 (向后兼容包装器)

    Returns:
        SenseVoiceService: SenseVoice服务实例
    """
    _ensure_log_configured()
    return get_asr_service("sense_voice")


def get_paraformer_model():
    """
    获取Paraformer模型 (向后兼容包装器)

    Returns:
        ParaformerService: Paraformer服务实例
    """
    _ensure_log_configured()
    return get_asr_service("paraformer")


def extract_audio_text_by_sense_voice(
    input_audio_path: str, task_id: Optional[str] = None
) -> str:
    """
    使用SenseVoice提取音频文本 (向后兼容包装器)

    Args:
        input_audio_path: 输入音频文件路径
        task_id: 任务ID

    Returns:
        str: 转录文本
    """
    _ensure_log_configured()
    return transcribe_audio(input_audio_path, "sense_voice", task_id)


def extract_audio_text_by_paraformer(
    input_audio_path: str, task_id: Optional[str] = None
) -> str:
    """
    使用Paraformer提取音频文本 (向后兼容包装器)

    Args:
        input_audio_path: 输入音频文件路径
        task_id: 任务ID

    Returns:
        str: 转录文本
    """
    _ensure_log_configured()
    return transcribe_audio(input_audio_path, "paraformer", task_id)


def extract_audio_text(
    input_audio_path: str, model_type: str = "paraformer", task_id: Optional[str] = None
) -> str:
    """
    提取音频文本 (向后兼容包装器)

    Args:
        input_audio_path: 输入音频文件路径
        model_type: 模型类型 ("sense_voice" 或 "paraformer")
        task_id: 任务ID

    Returns:
        str: 转录文本

    Raises:
        ValueError: 不支持的模型类型
        RuntimeError: 转录失败
        TaskCancelledException: 任务被取消
    """
    _ensure_log_configured()
    logger.info(
        f"Extracting text from audio: {input_audio_path} using model: {model_type}"
    )
    return transcribe_audio(input_audio_path, model_type, task_id)
