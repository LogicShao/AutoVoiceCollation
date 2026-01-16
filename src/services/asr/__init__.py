"""
ASR服务模块

提供FunASR模型(SenseVoice, Paraformer)的封装
"""

from .base import BaseASRService
from .factory import get_asr_service, transcribe_audio

__all__ = [
    "BaseASRService",
    "SenseVoiceService",
    "ParaformerService",
    "get_asr_service",
    "transcribe_audio",
]


def __getattr__(name):
    if name == "ParaformerService":
        from .paraformer import ParaformerService

        return ParaformerService
    if name == "SenseVoiceService":
        from .sense_voice import SenseVoiceService

        return SenseVoiceService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
