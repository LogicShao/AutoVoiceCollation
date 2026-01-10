"""
ASR服务模块

提供FunASR模型(SenseVoice, Paraformer)的封装
"""

from .base import BaseASRService
from .factory import get_asr_service, transcribe_audio
from .paraformer import ParaformerService
from .sense_voice import SenseVoiceService

__all__ = [
    "BaseASRService",
    "SenseVoiceService",
    "ParaformerService",
    "get_asr_service",
    "transcribe_audio",
]
