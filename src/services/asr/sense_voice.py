"""
SenseVoice ASR服务

封装SenseVoiceSmall模型的ASR功能
"""

from typing import Optional

from funasr import AutoModel

from src.text_arrangement.split_text import clean_asr_text
from src.utils.config import get_config

from .base import BaseASRService


class SenseVoiceService(BaseASRService):
    """SenseVoice ASR服务"""

    def __init__(self, device: str, onnx_providers: Optional[list] = None):
        """
        初始化SenseVoice服务

        Args:
            device: 设备类型 ('cpu', 'cuda', 'cuda:0' 等)
            onnx_providers: ONNX执行提供者列表
        """
        super().__init__()
        config = get_config()
        self.device = device
        self.onnx_providers = onnx_providers if config.asr.use_onnx else None

    def load_model(self):
        """加载SenseVoiceSmall模型"""
        if self.model is not None:
            return

        try:
            config = get_config()
            self.logger.info("Loading SenseVoiceSmall model...")

            model_kwargs = {
                "model": "iic/SenseVoiceSmall",
                "trust_remote_code": True,
                "remote_code": "./src/SenseVoiceSmall/model.py",
                "vad_model": "fsmn-vad",
                "vad_kwargs": {"max_single_segment_time": 30000},
                "device": self.device,
                "disable_update": True,
                "model_hub": "huggingface",
                "cache_dir": str(config.paths.model_dir)
                if config.paths.model_dir
                else None,
            }

            # 如果启用ONNX且有可用提供者
            if self.onnx_providers:
                try:
                    model_kwargs["onnx_providers"] = self.onnx_providers
                    self.logger.info("尝试使用 ONNX 推理模式")
                except Exception as e:
                    self.logger.warning(f"ONNX 参数设置失败，使用默认模式: {e}")

            self.model = AutoModel(**model_kwargs)
            self.logger.info("SenseVoiceSmall model loaded successfully.")

        except Exception as e:
            raise RuntimeError(f"Failed to load SenseVoiceSmall model: {e}")

    def transcribe(self, audio_path: str, task_id: Optional[str] = None) -> str:
        """
        使用SenseVoice转录音频

        Args:
            audio_path: 音频文件路径
            task_id: 任务ID

        Returns:
            str: 转录文本
        """
        # 检查任务是否被取消（模型加载前）
        self.check_cancellation(task_id)

        # 加载模型
        self.load_model()

        # 再次检查任务是否被取消（模型加载后、推理前）
        self.check_cancellation(task_id)

        try:
            self.logger.info(f"Transcribing audio with SenseVoice: {audio_path}")
            res = self.model.generate(
                input=audio_path,
                cache={},
                language="auto",  # "zh", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
            )

            text = clean_asr_text(res[0]["text"])
            return text

        except Exception as e:
            raise RuntimeError(f"Failed to transcribe audio with SenseVoice: {e}")
