"""
Paraformer ASR服务

封装Paraformer模型的ASR功能
"""

from typing import Optional

from funasr import AutoModel

from .base import BaseASRService

# 延迟导入配置，避免循环导入
import src.config as config


class ParaformerService(BaseASRService):
    """Paraformer ASR服务"""

    def __init__(self, device: str, onnx_providers: Optional[list] = None):
        """
        初始化Paraformer服务

        Args:
            device: 设备类型 ('cpu', 'cuda', 'cuda:0' 等)
            onnx_providers: ONNX执行提供者列表
        """
        super().__init__()
        self.device = device
        self.onnx_providers = onnx_providers if config.USE_ONNX else None

    def load_model(self):
        """加载Paraformer模型"""
        if self.model is not None:
            return

        try:
            self.logger.info("Loading Paraformer model...")

            model_kwargs = {
                "model": "paraformer-zh",
                "model_revision": "v2.0.4",
                "vad_model": "fsmn-vad",
                "vad_model_revision": "v2.0.4",
                "punc_model": "ct-punc-c",
                "punc_model_revision": "v2.0.4",
                "device": self.device,
                "disable_update": True,
                "model_hub": "huggingface",
                "cache_dir": config.MODEL_DIR,
            }

            # 如果启用ONNX且有可用提供者
            if self.onnx_providers:
                try:
                    model_kwargs["onnx_providers"] = self.onnx_providers
                    self.logger.info("尝试使用 ONNX 推理模式")
                except Exception as e:
                    self.logger.warning(f"ONNX 参数设置失败，使用默认模式: {e}")

            self.model = AutoModel(**model_kwargs)
            self.logger.info("Paraformer model loaded successfully.")

        except Exception as e:
            raise RuntimeError(f"Failed to load Paraformer model: {e}")

    def transcribe(self, audio_path: str, task_id: Optional[str] = None) -> str:
        """
        使用Paraformer转录音频

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
            self.logger.info(f"Transcribing audio with Paraformer: {audio_path}")
            res = self.model.generate(
                input=audio_path,
                batch_size_s=600,
            )

            return res[0]["text"]

        except Exception as e:
            raise RuntimeError(f"Failed to transcribe audio with Paraformer: {e}")
