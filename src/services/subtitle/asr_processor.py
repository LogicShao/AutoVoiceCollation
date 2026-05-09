"""ASR 处理器（字幕用）"""

from abc import ABC, abstractmethod

import soundfile as sf
import torch
import torchaudio

from src.SenseVoiceSmall.model import SenseVoiceSmall
from src.services.asr import get_asr_service
from src.text_arrangement.split_text import clean_asr_text
from src.utils.device.device_manager import detect_device as get_device
from src.utils.logging.logger import get_logger

from .config import SubtitleConfig
from .models import ASRResult
from .utils import TempFileManager

logger = get_logger(__name__)


class AudioSlicer:
    """音频切片器"""

    def __init__(self, config: SubtitleConfig):
        self.config = config

    def slice(
        self, audio_path: str, batch_size_s: float
    ) -> list[tuple[torch.Tensor, float, float]]:
        """
        将音频切分为固定长度的片段

        返回: [(音频张量, 开始时间, 结束时间), ...]
        """
        audio, sr = torchaudio.load(audio_path)
        if sr != self.config.sample_rate:
            audio = torchaudio.functional.resample(audio, sr, self.config.sample_rate)

        total_samples = audio.shape[1]
        samples_per_slice = int(batch_size_s * self.config.sample_rate)

        slices = []
        for i in range(0, total_samples, samples_per_slice):
            start = i
            end = min(i + samples_per_slice, total_samples)
            slice_audio = audio[:, start:end]
            start_time = start / self.config.sample_rate
            end_time = end / self.config.sample_rate
            slices.append((slice_audio, start_time, end_time))

        logger.debug(f"音频切分完成，共 {len(slices)} 个片段")
        return slices


class ASRProcessor(ABC):
    """ASR 处理器抽象基类"""

    @abstractmethod
    def process(self, audio_path: str) -> ASRResult:
        """处理音频文件，返回识别结果"""
        pass


class SenseVoiceProcessor(ASRProcessor):
    """SenseVoice ASR 处理器"""

    def __init__(self, config: SubtitleConfig, device: str | None = None):
        self.config = config
        self.device = device or get_device()
        self.model = None
        self.kwargs = None
        self.audio_slicer = AudioSlicer(config)

    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            model_dir = "iic/SenseVoiceSmall"
            logger.info(f"正在加载 SenseVoice 模型，设备: {self.device}")
            self.model, self.kwargs = SenseVoiceSmall.from_pretrained(
                model=model_dir, device=self.device
            )
            self.model.eval()

    def process(self, audio_path: str) -> ASRResult:
        """处理音频文件"""
        self._load_model()

        slices = self.audio_slicer.slice(audio_path, self.config.batch_size_s)
        all_results = []

        with TempFileManager(self.config.temp_dir) as temp_mgr:
            for idx, (audio_tensor, t_start, t_end) in enumerate(slices):
                logger.info(f"处理片段 {idx + 1}/{len(slices)}: {t_start:.2f}s - {t_end:.2f}s")

                temp_path = temp_mgr.create_temp_file("clip", ".wav")
                sf.write(
                    str(temp_path),
                    audio_tensor.T.numpy(),
                    samplerate=self.config.sample_rate,
                    format="WAV",
                    subtype="PCM_16",
                )

                try:
                    with torch.no_grad():
                        res = self.model.inference(
                            data_in=str(temp_path),
                            language="auto",
                            use_itn=False,
                            ban_emo_unk=True,
                            output_timestamp=True,
                            **self.kwargs,
                        )
                except Exception as e:
                    logger.error(f"处理片段 {idx + 1} 时出错: {e}")
                    continue

                # 修正时间戳为全局时间
                for item in res[0]:
                    text = self._clean_text(item["text"])
                    timestamp = [
                        [
                            self._clean_text(lst[0]),
                            round(lst[1] + t_start, 2),
                            round(lst[2] + t_start, 2),
                        ]
                        for lst in item["timestamp"]
                        if self._clean_text(lst[0]) != ""
                    ]
                    all_results.append({"text": text, "timestamp": timestamp})

        # 合并结果
        full_text = clean_asr_text("".join(item["text"] for item in all_results))
        full_timestamp = sum([item["timestamp"] for item in all_results], start=[])

        return ASRResult(text=full_text, timestamp=full_timestamp)

    @staticmethod
    def _clean_text(text: str) -> str:
        """清理文本中的特殊字符"""
        return text.replace("_", "").replace("▁", "")


class ParaformerProcessor(ASRProcessor):
    """Paraformer ASR 处理器"""

    def __init__(self, config: SubtitleConfig):
        self.config = config
        self.model = None
        self.audio_slicer = AudioSlicer(config)

    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            logger.info("正在加载 Paraformer 模型")
            self.model = get_asr_service("paraformer")

    def process(self, audio_path: str) -> ASRResult:
        """
        处理音频文件（使用分块处理提高长视频的时间精度）

        注意：Paraformer 返回的是句子级别的时间戳，需要插值生成字符级别的时间戳
        """
        self._load_model()

        # 使用配置的分块大小（默认30秒）
        chunk_size_s = self.config.paraformer_chunk_size_s
        slices = self.audio_slicer.slice(audio_path, chunk_size_s)

        all_results = []

        with TempFileManager(self.config.temp_dir) as temp_mgr:
            for idx, (audio_tensor, t_start, t_end) in enumerate(slices):
                logger.info(f"处理片段 {idx + 1}/{len(slices)}: {t_start:.2f}s - {t_end:.2f}s")

                # 保存临时音频文件
                temp_path = temp_mgr.create_temp_file("para_clip", ".wav")
                sf.write(
                    str(temp_path),
                    audio_tensor.T.numpy(),
                    samplerate=self.config.sample_rate,
                    format="WAV",
                    subtype="PCM_16",
                )

                try:
                    # 处理当前音频片段
                    res = self.model.generate_with_timestamps(
                        audio_path=str(temp_path),
                        batch_size_s=self.config.paraformer_batch_size_s,
                    )

                    text = res[0]["text"]
                    sentence_timestamps = res[0]["timestamp"]  # [[begin_ms, end_ms], ...]

                    # 将句子级别的时间戳插值为字符级别
                    char_timestamps = self._interpolate_char_timestamps(text, sentence_timestamps)

                    # 修正时间戳为全局时间（加上片段起始时间偏移）
                    adjusted_timestamps = [
                        (char, start + t_start, end + t_start)
                        for char, start, end in char_timestamps
                    ]

                    all_results.append({"text": text, "timestamp": adjusted_timestamps})

                except Exception as e:
                    logger.error(f"处理片段 {idx + 1} 时出错: {e}")
                    continue

        # 合并所有片段的结果
        full_text = "".join(item["text"] for item in all_results)
        full_timestamp = sum([item["timestamp"] for item in all_results], start=[])

        logger.info(
            f"Paraformer 分块处理完成，共 {len(slices)} 个片段，分块大小: {chunk_size_s}秒，总文本长度: {len(full_text)}"
        )
        return ASRResult(text=full_text, timestamp=full_timestamp)

    def _interpolate_char_timestamps(
        self, text: str, sentence_timestamps: list[list[int]]
    ) -> list[tuple[str, float, float]]:
        """
        将句子级别的时间戳插值为字符级别

        Args:
            text: 完整文本
            sentence_timestamps: 句子级别的时间戳 [[begin_ms, end_ms], ...]

        Returns:
            字符级别的时间戳 [(char, start_sec, end_sec), ...]
        """
        char_timestamps = []

        if not sentence_timestamps:
            # 如果没有时间戳，生成虚拟时间戳
            for i, char in enumerate(text):
                char_timestamps.append((char, float(i) * 0.1, float(i + 1) * 0.1))
            return char_timestamps

        # 将时间戳从毫秒转换为秒
        sentence_timestamps_sec = [
            [begin / 1000.0, end / 1000.0] for begin, end in sentence_timestamps
        ]

        # 获取总时长
        total_start = sentence_timestamps_sec[0][0]
        total_end = sentence_timestamps_sec[-1][1]
        total_duration = total_end - total_start

        # 计算每个字符的平均时长
        text_len = len(text)
        if text_len == 0:
            return []

        avg_char_duration = total_duration / text_len

        # 为每个字符分配时间戳（线性插值）
        for i, char in enumerate(text):
            start_time = total_start + i * avg_char_duration
            end_time = total_start + (i + 1) * avg_char_duration
            char_timestamps.append((char, round(start_time, 2), round(end_time, 2)))

        logger.debug(f"生成字符级别时间戳: {len(char_timestamps)} 个字符")
        return char_timestamps
