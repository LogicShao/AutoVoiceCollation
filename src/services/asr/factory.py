"""
ASR服务工厂

提供ASR服务的创建和管理
"""

from src.utils.config import get_config
from src.utils.device.device_manager import detect_device, get_onnx_providers
from src.utils.logging.logger import get_logger

from .base import BaseASRService
from .preprocess import cleanup_preprocessed_audio, prepare_asr_audio

logger = get_logger(__name__)

# 获取配置
config = get_config()

# 全局单例缓存
_sense_voice_instance: BaseASRService | None = None
_paraformer_instance: BaseASRService | None = None
_whisper_cpp_instance: BaseASRService | None = None


def get_asr_service(model_type: str = "paraformer") -> BaseASRService:
    """
    获取ASR服务实例（单例模式）

    Args:
        model_type: 模型类型 ('sense_voice' 或 'paraformer')

    Returns:
        BaseASRService: ASR服务实例

    Raises:
        ValueError: 不支持的模型类型
    """
    global _sense_voice_instance, _paraformer_instance, _whisper_cpp_instance

    model_type = (model_type or "paraformer").lower().strip()

    if model_type == "whisper_cpp":
        if _whisper_cpp_instance is None:
            from .whisper_cpp import WhisperCppService

            logger.info("Creating whisper.cpp service instance")
            _whisper_cpp_instance = WhisperCppService()
        return _whisper_cpp_instance

    # 检测设备（仅用于 FunASR）
    device = detect_device(config.asr.device)

    onnx_providers = None
    if config.asr.use_onnx:
        custom_providers = config.asr.onnx_providers.strip() or None
        onnx_providers = get_onnx_providers(device, custom_providers)

    if model_type == "sense_voice":
        if _sense_voice_instance is None:
            from .sense_voice import SenseVoiceService

            logger.info(f"Creating SenseVoice service instance (device: {device})")
            _sense_voice_instance = SenseVoiceService(device, onnx_providers)
        return _sense_voice_instance

    if model_type == "paraformer":
        if _paraformer_instance is None:
            from .paraformer import ParaformerService

            logger.info(f"Creating Paraformer service instance (device: {device})")
            _paraformer_instance = ParaformerService(device, onnx_providers)
        return _paraformer_instance

    raise ValueError(
        f"Unsupported model type: {model_type}. Supported types: 'sense_voice', 'paraformer', 'whisper_cpp'"
    )


def transcribe_audio(
    audio_path: str, model_type: str = "paraformer", task_id: str | None = None
) -> str:
    """
    转录音频文件（便捷函数）

    Args:
        audio_path: 音频文件路径
        model_type: 模型类型 ('sense_voice' 或 'paraformer')
        task_id: 任务ID

    Returns:
        str: 转录文本

    Raises:
        ValueError: 不支持的模型类型
        RuntimeError: 转录失败
        TaskCancelledException: 任务被取消
    """
    service = get_asr_service(model_type)
    processed_path = None
    is_temp = False
    try:
        processed_path, is_temp = prepare_asr_audio(audio_path, task_id=task_id)
        return service.transcribe(str(processed_path), task_id)
    finally:
        if is_temp and processed_path is not None and not config.debug_flag:
            cleanup_preprocessed_audio(processed_path)
