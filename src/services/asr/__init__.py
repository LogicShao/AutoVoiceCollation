"""
ASR服务模块

提供FunASR模型(SenseVoice, Paraformer)的封装
"""

from .base import BaseASRService
from .sense_voice import SenseVoiceService
from .paraformer import ParaformerService
from .factory import get_asr_service, transcribe_audio

__all__ = [
    "BaseASRService",
    "SenseVoiceService",
    "ParaformerService",
    "get_asr_service",
    "transcribe_audio",
]
