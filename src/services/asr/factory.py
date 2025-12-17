"""
ASR服务工厂

提供ASR服务的创建和管理
"""

from typing import Optional

from src.device_manager import detect_device, get_onnx_providers
from src.logger import get_logger

from .base import BaseASRService
from .sense_voice import SenseVoiceService
from .paraformer import ParaformerService

# 延迟导入配置，避免循环导入
import src.config as config


logger = get_logger(__name__)

# 全局单例缓存
_sense_voice_instance: Optional[SenseVoiceService] = None
_paraformer_instance: Optional[ParaformerService] = None


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
    global _sense_voice_instance, _paraformer_instance

    # 检测设备
    device = detect_device(config.DEVICE)
    onnx_providers = get_onnx_providers(device, config.ONNX_PROVIDERS)

    if model_type == "sense_voice":
        if _sense_voice_instance is None:
            logger.info(f"Creating SenseVoice service instance (device: {device})")
            _sense_voice_instance = SenseVoiceService(device, onnx_providers)
        return _sense_voice_instance

    elif model_type == "paraformer":
        if _paraformer_instance is None:
            logger.info(f"Creating Paraformer service instance (device: {device})")
            _paraformer_instance = ParaformerService(device, onnx_providers)
        return _paraformer_instance

    else:
        raise ValueError(
            f"Unsupported model type: {model_type}. "
            f"Supported types: 'sense_voice', 'paraformer'"
        )


def transcribe_audio(
    audio_path: str, model_type: str = "paraformer", task_id: Optional[str] = None
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
    return service.transcribe(audio_path, task_id)
