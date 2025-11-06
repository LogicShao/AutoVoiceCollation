import difflib
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import List, Tuple, Optional

import jieba
import soundfile as sf
import torch
import torchaudio

from src.SenseVoiceSmall.model import SenseVoiceSmall
from src.device_manager import detect_device as get_device
from src.extract_audio_text import get_paraformer_model
from src.logger import get_logger
from src.text_arrangement.query_llm import query_llm, LLMQueryParams
from src.text_arrangement.split_text import clean_asr_text, smart_split

logger = get_logger(__name__)


# ============================================================================
# 配置类
# ============================================================================

@dataclass
class SubtitleConfig:
    """字幕生成配置"""
    # 分段参数
    pause_threshold: float = 0.6  # 停顿阈值（秒）
    max_chars_per_segment: int = 16  # 每段最大字符数

    # LLM 参数
    llm_split_len: int = 600  # LLM 处理的最大文本长度
    llm_max_tokens: int = 1000
    llm_temperature: float = 0.0
    llm_top_p: float = 0.95
    llm_top_k: int = 1
    llm_retry: int = 3

    # ASR 参数
    batch_size_s: int = 5  # SenseVoice 批处理大小（秒）
    paraformer_batch_size_s: int = 900  # Paraformer 批处理大小（秒）
    paraformer_chunk_size_s: int = 30  # Paraformer 音频分块大小（秒，用于提高长视频时间精度）
    sample_rate: int = 16000

    # 文本匹配参数
    max_edit_distance: int = 5  # 最大编辑距离

    # 临时目录
    temp_dir: Path = Path("./temp")


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class SubtitleSegment:
    """字幕片段"""
    text: str
    start_time: float  # 秒
    end_time: float  # 秒

    def duration(self) -> float:
        """获取片段时长"""
        return self.end_time - self.start_time

    def __str__(self) -> str:
        return f"[{self.start_time:.2f}s - {self.end_time:.2f}s] {self.text}"


@dataclass
class ASRResult:
    """ASR 识别结果"""
    text: str
    timestamp: List[Tuple[str, float, float]]  # [(字符, 开始时间, 结束时间), ...]

    def get_clean_text(self) -> str:
        """获取清理后的文本"""
        return clean_asr_text(self.text)


# ============================================================================
# 工具类
# ============================================================================

class TimestampFormatter:
    """时间戳格式化工具"""

    @staticmethod
    def to_srt(seconds: float) -> str:
        """转换为 SRT 格式：HH:MM:SS,mmm"""
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((td.total_seconds() - total_seconds) * 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

    @staticmethod
    def to_cc(seconds: float) -> str:
        """转换为 CC 格式：HH:MM:SS.mmmm"""
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((td.total_seconds() - total_seconds) * 10000)
        return f"{hours:02}:{minutes:02}:{secs:02}.{milliseconds:04}"


class PathHelper:
    """路径处理工具"""

    @staticmethod
    def normalize_for_ffmpeg(path: str) -> str:
        """标准化路径为 FFmpeg 格式（正斜杠）"""
        return path.replace("\\", "/")

    @staticmethod
    def escape_for_ffmpeg_filter(path: str) -> str:
        """转义路径用于 FFmpeg 过滤器（需要转义冒号）"""
        return PathHelper.normalize_for_ffmpeg(path).replace(":", "\\\\:")


class TextMatcher:
    """文本匹配工具"""

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """计算编辑距离"""
        len_s1, len_s2 = len(s1), len(s2)
        dp = [[0] * (len_s2 + 1) for _ in range(len_s1 + 1)]

        for i in range(len_s1 + 1):
            dp[i][0] = i
        for j in range(len_s2 + 1):
            dp[0][j] = j

        for i in range(1, len_s1 + 1):
            for j in range(1, len_s2 + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = min(
                        dp[i - 1][j] + 1,  # 删除
                        dp[i][j - 1] + 1,  # 插入
                        dp[i - 1][j - 1] + 1  # 替换
                    )
        return dp[len_s1][len_s2]

    @staticmethod
    def is_similar(s1: str, s2: str, max_distance: int) -> bool:
        """判断两个字符串是否相似"""
        return TextMatcher.levenshtein_distance(s1, s2) <= max_distance

    @staticmethod
    def align_text_segments(segments: List[str], original: str, max_distance: int) -> List[str]:
        """
        将 LLM 切分的文本段与原始文本对齐

        原理：使用序列匹配算法在原文中查找每个段落的最佳匹配位置
        """
        processed = ''.join(segments)
        if not TextMatcher.is_similar(processed, original, max_distance):
            logger.warning(f"切分文本与原文差异过大，放弃对齐")
            return []

        aligned = []
        cursor = 0  # 原文当前搜索位置

        for seg in segments:
            search_window = original[cursor:]
            matcher = difflib.SequenceMatcher(None, seg, search_window)
            match = matcher.find_longest_match(0, len(seg), 0, len(search_window))

            if match.size == 0:
                logger.warning(f"无法匹配片段: {seg[:20]}...")
                return []

            start = cursor + match.b
            end = max(start + match.size, start + len(seg))
            end = min(end, len(original))

            aligned.append(original[start:end])
            cursor = end

        return aligned


class TempFileManager:
    """临时文件管理器"""

    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._created_files: List[Path] = []

    def create_temp_file(self, prefix: str, suffix: str) -> Path:
        """创建临时文件路径"""
        idx = len(self._created_files)
        temp_path = self.temp_dir / f"{prefix}_{idx}{suffix}"
        self._created_files.append(temp_path)
        return temp_path

    def cleanup(self):
        """清理所有临时文件"""
        for file_path in self._created_files:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"已删除临时文件: {file_path}")
        self._created_files.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


# ============================================================================
# 音频处理类
# ============================================================================

class AudioSlicer:
    """音频切片器"""

    def __init__(self, config: SubtitleConfig):
        self.config = config

    def slice(self, audio_path: str, batch_size_s: float) -> List[Tuple[torch.Tensor, float, float]]:
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


# ============================================================================
# ASR 处理类
# ============================================================================

class ASRProcessor(ABC):
    """ASR 处理器抽象基类"""

    @abstractmethod
    def process(self, audio_path: str) -> ASRResult:
        """处理音频文件，返回识别结果"""
        pass


class SenseVoiceProcessor(ASRProcessor):
    """SenseVoice ASR 处理器"""

    def __init__(self, config: SubtitleConfig, device: Optional[str] = None):
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
                model=model_dir,
                device=self.device
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
                    format='WAV',
                    subtype='PCM_16'
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
                        [self._clean_text(lst[0]), round(lst[1] + t_start, 2), round(lst[2] + t_start, 2)]
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
            self.model = get_paraformer_model()

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
                    format='WAV',
                    subtype='PCM_16'
                )

                try:
                    # 处理当前音频片段
                    res = self.model.generate(
                        input=str(temp_path),
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

                    all_results.append({
                        "text": text,
                        "timestamp": adjusted_timestamps
                    })

                except Exception as e:
                    logger.error(f"处理片段 {idx + 1} 时出错: {e}")
                    continue

        # 合并所有片段的结果
        full_text = "".join(item["text"] for item in all_results)
        full_timestamp = sum([item["timestamp"] for item in all_results], start=[])

        logger.info(
            f"Paraformer 分块处理完成，共 {len(slices)} 个片段，分块大小: {chunk_size_s}秒，总文本长度: {len(full_text)}")
        return ASRResult(text=full_text, timestamp=full_timestamp)

    def _interpolate_char_timestamps(
            self,
            text: str,
            sentence_timestamps: List[List[int]]
    ) -> List[Tuple[str, float, float]]:
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
            [begin / 1000.0, end / 1000.0]
            for begin, end in sentence_timestamps
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


# ============================================================================
# 字幕分段器
# ============================================================================

class SubtitleSegmenter(ABC):
    """字幕分段器抽象基类"""

    @abstractmethod
    def segment(self, asr_result: ASRResult) -> List[SubtitleSegment]:
        """将 ASR 结果分段为字幕片段"""
        pass


class PauseBasedSegmenter(SubtitleSegmenter):
    """基于停顿和语义的分段器"""

    def __init__(self, config: SubtitleConfig):
        self.config = config

    def segment(self, asr_result: ASRResult) -> List[SubtitleSegment]:
        """基于停顿和语义进行分段"""
        if not asr_result.timestamp:
            return []

        segments = []
        current_chars = []
        current_text = ""
        current_start = asr_result.timestamp[0][1]

        for i, (char, start, end) in enumerate(asr_result.timestamp):
            if not current_chars:
                current_start = start

            current_chars.append((char, start, end))
            current_text += char

            # 计算到下一个字符的停顿时间
            next_pause = 0.0
            if i + 1 < len(asr_result.timestamp):
                next_pause = asr_result.timestamp[i + 1][1] - end

            # 判断是否需要分段
            over_length = len(current_text) >= self.config.max_chars_per_segment
            is_pause = next_pause > self.config.pause_threshold

            if over_length or is_pause:
                # 使用分词判断语义边界
                if self._is_semantic_boundary(current_text) or is_pause:
                    segments.append(SubtitleSegment(
                        text=current_text,
                        start_time=current_start,
                        end_time=end
                    ))
                    current_chars = []
                    current_text = ""

        # 处理剩余部分
        if current_chars:
            segments.append(SubtitleSegment(
                text=current_text,
                start_time=current_start,
                end_time=current_chars[-1][2]
            ))

        logger.info(f"基于停顿分段完成，共 {len(segments)} 个片段")
        return segments

    @staticmethod
    def _is_semantic_boundary(text: str) -> bool:
        """判断是否为语义边界"""
        words = list(jieba.cut(text))
        return len(words) > 1


class PunctuationPauseSegmenter(SubtitleSegmenter):
    """基于标点符号和停顿的分段器（优先标点符号）"""

    # 中文标点符号（强分段符号）
    STRONG_PUNCTUATION = '。？！；\n'
    # 中文标点符号（弱分段符号）
    WEAK_PUNCTUATION = '，、：'

    def __init__(self, config: SubtitleConfig):
        self.config = config

    def segment(self, asr_result: ASRResult) -> List[SubtitleSegment]:
        """
        基于标点符号和停顿进行分段

        优先级：
        1. 强标点符号（。？！；）：必定分段
        2. 弱标点符号（，、：）+ 超过最小长度：分段
        3. 超过最大长度 + 停顿：分段
        """
        if not asr_result.timestamp:
            return []

        segments = []
        current_chars = []
        current_text = ""
        current_start = asr_result.timestamp[0][1]

        # 最小分段长度（避免段落过短）
        min_segment_length = max(8, self.config.max_chars_per_segment // 2)

        for i, (char, start, end) in enumerate(asr_result.timestamp):
            if not current_chars:
                current_start = start

            current_chars.append((char, start, end))
            current_text += char

            # 计算到下一个字符的停顿时间
            next_pause = 0.0
            if i + 1 < len(asr_result.timestamp):
                next_pause = asr_result.timestamp[i + 1][1] - end

            # 判断分段条件
            current_len = len(current_text)
            is_strong_punctuation = char in self.STRONG_PUNCTUATION
            is_weak_punctuation = char in self.WEAK_PUNCTUATION and current_len >= min_segment_length
            is_over_length = current_len >= self.config.max_chars_per_segment
            is_pause = next_pause > self.config.pause_threshold and current_len >= min_segment_length

            # 分段决策
            should_segment = False

            if is_strong_punctuation:
                # 强标点符号：必定分段
                should_segment = True
                logger.debug(f"强标点分段: '{current_text[-10:]}' (长度: {current_len})")

            elif is_weak_punctuation:
                # 弱标点符号 + 达到最小长度：分段
                should_segment = True
                logger.debug(f"弱标点分段: '{current_text[-10:]}' (长度: {current_len})")

            elif is_over_length:
                # 超过最大长度：寻找最近的标点或停顿
                if is_pause:
                    should_segment = True
                    logger.debug(f"超长+停顿分段: '{current_text[-10:]}' (长度: {current_len})")
                elif self._is_semantic_boundary(current_text):
                    should_segment = True
                    logger.debug(f"超长+语义分段: '{current_text[-10:]}' (长度: {current_len})")

            elif is_pause:
                # 仅停顿：分段
                should_segment = True
                logger.debug(f"停顿分段: '{current_text[-10:]}' (长度: {current_len})")

            if should_segment:
                segments.append(SubtitleSegment(
                    text=current_text.strip(),
                    start_time=current_start,
                    end_time=end
                ))
                current_chars = []
                current_text = ""

        # 处理剩余部分
        if current_chars:
            segments.append(SubtitleSegment(
                text=current_text.strip(),
                start_time=current_start,
                end_time=current_chars[-1][2]
            ))

        logger.info(f"基于标点符号+停顿分段完成，共 {len(segments)} 个片段")
        return segments

    @staticmethod
    def _is_semantic_boundary(text: str) -> bool:
        """判断是否为语义边界"""
        words = list(jieba.cut(text))
        return len(words) > 1


class LLMBasedSegmenter(SubtitleSegmenter):
    """基于 LLM 的智能分段器"""

    def __init__(self, config: SubtitleConfig, api_server: str, fallback_segmenter: SubtitleSegmenter):
        self.config = config
        self.api_server = api_server
        self.fallback_segmenter = fallback_segmenter
        self.text_matcher = TextMatcher()

    def segment(self, asr_result: ASRResult) -> List[SubtitleSegment]:
        """使用 LLM 进行智能分段"""
        if not asr_result.timestamp:
            return []

        # 验证参数
        if self.config.llm_split_len > self.config.llm_max_tokens:
            raise ValueError(
                f"llm_split_len ({self.config.llm_split_len}) 不能超过 llm_max_tokens ({self.config.llm_max_tokens})")

        full_text = asr_result.text
        full_text_clean = full_text.replace(" ", "")

        # 将长文本切分为块
        text_chunks = smart_split(full_text, split_len=self.config.llm_split_len)

        segments = []
        time_cursor = 0  # 时间戳数组的游标

        for chunk in text_chunks:
            chunk_clean = chunk.replace(" ", "").replace("\n", "")
            chunk_segments = self._segment_chunk(chunk_clean, asr_result.timestamp, time_cursor)

            if chunk_segments:
                segments.extend(chunk_segments)
                # 更新游标：已处理的字符数
                time_cursor += len(chunk_clean)
            else:
                # LLM 分段失败，使用回退策略
                logger.warning(f"LLM 分段失败，使用回退策略处理该块")
                # 找到该块对应的时间戳范围
                start_idx = time_cursor
                end_idx = time_cursor + len(chunk_clean)
                partial_result = ASRResult(
                    text=chunk_clean,
                    timestamp=asr_result.timestamp[start_idx:end_idx]
                )
                fallback_segments = self.fallback_segmenter.segment(partial_result)
                segments.extend(fallback_segments)
                time_cursor = end_idx

        logger.info(f"LLM 分段完成，共 {len(segments)} 个片段")
        return segments

    def _segment_chunk(
            self,
            chunk: str,
            full_timestamp: List[Tuple[str, float, float]],
            time_cursor: int
    ) -> List[SubtitleSegment]:
        """
        使用 LLM 分段单个文本块

        Args:
            chunk: 要分段的文本块
            full_timestamp: 完整的时间戳数组
            time_cursor: 当前在时间戳数组中的位置
        """
        system_instruction = (
            f"你是一个字幕切分助手。请将以下文本切分为适合显示的多行字幕。"
            f"每行最长 {self.config.max_chars_per_segment} 个字符。"
            f"在每个切分点用 '|' 分隔，不要换行，不要添加、删除或替换任何文字。"
        )

        llm_params = LLMQueryParams(
            content=chunk,
            system_instruction=system_instruction,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
            api_server=self.api_server,
            top_p=self.config.llm_top_p,
            top_k=self.config.llm_top_k
        )

        # 尝试多次查询
        for attempt in range(self.config.llm_retry):
            logger.info(f"LLM 查询尝试 {attempt + 1}/{self.config.llm_retry}，文本长度: {len(chunk)}")

            try:
                response = query_llm(llm_params)
                response_clean = response.replace(" ", "").replace("\n", "")
                split_parts = response_clean.split("|")

                # 验证响应
                if self.text_matcher.is_similar(
                        ''.join(split_parts),
                        chunk,
                        self.config.max_edit_distance
                ):
                    logger.info("LLM 分段成功")
                    return self._align_segments_with_timestamp(
                        split_parts, chunk, full_timestamp, time_cursor
                    )
                else:
                    logger.warning(f"LLM 响应与原文不匹配，尝试 {attempt + 1}")

            except Exception as e:
                logger.error(f"LLM 查询出错: {e}")

        logger.warning(f"LLM 查询失败，已重试 {self.config.llm_retry} 次")
        return []

    def _align_segments_with_timestamp(
            self,
            split_parts: List[str],
            original_chunk: str,
            full_timestamp: List[Tuple[str, float, float]],
            time_cursor: int
    ) -> List[SubtitleSegment]:
        """将 LLM 切分的文本段与时间戳对齐"""
        # 修复切分结果
        aligned_parts = TextMatcher.align_text_segments(
            split_parts,
            original_chunk,
            self.config.max_edit_distance
        )

        if not aligned_parts:
            return []

        segments = []
        local_cursor = 0  # 在当前块内的字符游标

        for part in aligned_parts:
            # 收集该段对应的时间戳
            part_chars = []
            matched_text = ""

            while matched_text != part and (time_cursor + local_cursor) < len(full_timestamp):
                char_info = full_timestamp[time_cursor + local_cursor]
                part_chars.append(char_info)
                matched_text += char_info[0]
                local_cursor += 1

            if part_chars:
                segments.append(SubtitleSegment(
                    text=part,
                    start_time=part_chars[0][1],
                    end_time=part_chars[-1][2]
                ))

        return segments


# ============================================================================
# 字幕文件生成器
# ============================================================================

class SubtitleFileGenerator:
    """字幕文件生成器"""

    @staticmethod
    def generate_srt(segments: List[SubtitleSegment], output_path: str) -> str:
        """生成 SRT 字幕文件"""
        lines = []
        for idx, seg in enumerate(segments, 1):
            start_ts = TimestampFormatter.to_srt(seg.start_time)
            end_ts = TimestampFormatter.to_srt(seg.end_time)
            lines.append(f"{idx}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(seg.text.strip())
            lines.append("")  # 空行分隔

        content = "\n".join(lines)
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(content)

        logger.info(f"SRT 字幕文件已生成: {output_path}")
        return output_path

    @staticmethod
    def generate_cc(segments: List[SubtitleSegment], output_path: str) -> str:
        """生成 CC 字幕文件"""
        lines = []
        for seg in segments:
            start_ts = TimestampFormatter.to_cc(seg.start_time)
            end_ts = TimestampFormatter.to_cc(seg.end_time)
            lines.append(f"{start_ts} {end_ts} {seg.text.strip()}")

        content = "\n".join(lines)
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(content)

        logger.info(f"CC 字幕文件已生成: {output_path}")
        return output_path


# ============================================================================
# 视频硬编码器
# ============================================================================

class SubtitleVideoEncoder:
    """字幕视频硬编码器"""

    @staticmethod
    def encode(video_path: str, srt_path: str, output_path: Optional[str] = None) -> str:
        """
        将 SRT 字幕硬编码到视频中

        Args:
            video_path: 输入视频路径
            srt_path: SRT 字幕文件路径
            output_path: 输出视频路径（可选）

        Returns:
            输出视频路径
        """
        # 验证输入文件
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        if not os.path.isfile(srt_path):
            raise FileNotFoundError(f"字幕文件不存在: {srt_path}")

        # 确定输出路径
        if output_path is None:
            base_name = os.path.splitext(video_path)[0]
            output_path = f"{base_name}-with-subtitles.mp4"

        # 准备 FFmpeg 路径
        video_ffmpeg = PathHelper.normalize_for_ffmpeg(video_path)
        srt_ffmpeg = PathHelper.escape_for_ffmpeg_filter(srt_path)
        output_ffmpeg = PathHelper.normalize_for_ffmpeg(output_path)

        # 构建 FFmpeg 命令
        command = [
            'ffmpeg',
            '-i', video_ffmpeg,
            '-vf', f'subtitles={srt_ffmpeg}',
            '-c:a', 'copy',
            '-y',  # 覆盖已存在的文件
            output_ffmpeg
        ]

        logger.info(f"开始硬编码字幕: {output_path}")
        logger.debug(f"FFmpeg 命令: {' '.join(command)}")

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0:
            raise RuntimeError(f"字幕硬编码失败:\n{result.stderr}")

        logger.info(f"字幕硬编码成功: {output_path}")
        return output_path


# ============================================================================
# 高层 API
# ============================================================================

def generate_subtitle_file(
        audio_path: str,
        output_path: Optional[str] = None,
        file_type: str = 'srt',
        model: str = 'paraformer',
        segmenter_type: str = 'pause',
        config: Optional[SubtitleConfig] = None,
        api_server: str = 'gemini-2.0-flash',
        paraformer_chunk_size_s: int = 30
) -> str:
    """
    生成字幕文件（高层 API）

    Args:
        audio_path: 音频文件路径
        output_path: 输出文件路径（可选，默认为音频文件同名）
        file_type: 字幕文件类型 ('srt' 或 'cc')
        model: ASR 模型 ('paraformer' 或 'sense_voice')
        segmenter_type: 分段策略 ('pause', 'punctuation', 'llm')
        config: 配置对象（可选）
        api_server: LLM API 服务器（当 segmenter_type='llm' 时使用）
        paraformer_chunk_size_s: Paraformer 分块大小（秒，默认30秒）

    Returns:
        生成的字幕文件路径
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    if file_type not in ['srt', 'cc']:
        raise ValueError(f"不支持的字幕格式: {file_type}")

    # 使用默认配置或更新配置
    if config is None:
        config = SubtitleConfig()

    # 更新 Paraformer 分块大小
    config.paraformer_chunk_size_s = paraformer_chunk_size_s

    # 确定输出路径
    if output_path is None:
        base_name = os.path.splitext(audio_path)[0]
        output_path = f"{base_name}.{file_type}"

    # 1. ASR 识别
    logger.info(f"使用 {model} 模型进行语音识别")
    if model == 'sense_voice':
        asr_processor = SenseVoiceProcessor(config)
    elif model == 'paraformer':
        asr_processor = ParaformerProcessor(config)
    else:
        raise ValueError(f"不支持的 ASR 模型: {model}")

    asr_result = asr_processor.process(audio_path)

    # 2. 字幕分段
    logger.info(f"使用 {segmenter_type} 策略进行字幕分段")
    if segmenter_type == 'pause':
        segmenter = PauseBasedSegmenter(config)
    elif segmenter_type == 'punctuation':
        segmenter = PunctuationPauseSegmenter(config)
    elif segmenter_type == 'llm':
        fallback = PunctuationPauseSegmenter(config)  # 使用标点分段作为回退策略
        segmenter = LLMBasedSegmenter(config, api_server, fallback)
    else:
        raise ValueError(f"不支持的分段策略: {segmenter_type}")

    segments = segmenter.segment(asr_result)

    if not segments:
        raise ValueError("未能生成任何字幕片段")

    # 3. 生成字幕文件
    logger.info(f"生成 {file_type.upper()} 字幕文件")
    if file_type == 'srt':
        return SubtitleFileGenerator.generate_srt(segments, output_path)
    else:
        return SubtitleFileGenerator.generate_cc(segments, output_path)


def encode_subtitle_to_video(
        video_path: str,
        srt_path: str,
        output_path: Optional[str] = None
) -> str:
    """
    将字幕硬编码到视频中（高层 API）

    Args:
        video_path: 视频文件路径
        srt_path: SRT 字幕文件路径
        output_path: 输出视频路径（可选）

    Returns:
        输出视频路径
    """
    return SubtitleVideoEncoder.encode(video_path, srt_path, output_path)


# ============================================================================
# 兼容性包装器（向后兼容旧接口）
# ============================================================================

def gen_timestamped_text_file(
        audio_path: str,
        file_type: str = 'srt',
        batch_size_s: int = 5,
        model: str = 'paraformer'
) -> str:
    """
    向后兼容的函数（旧接口）
    """
    config = SubtitleConfig(batch_size_s=batch_size_s)
    return generate_subtitle_file(
        audio_path=audio_path,
        file_type=file_type,
        model=model,
        config=config
    )


def hard_encode_dot_srt_file(
        input_video_path: str,
        input_srt_path: str,
        output_video_path: Optional[str] = None
) -> str:
    """
    向后兼容的函数（旧接口）
    """
    return encode_subtitle_to_video(input_video_path, input_srt_path, output_video_path)


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == "__main__":
    import sys
    from src.bilibili_downloader import extract_audio_from_video, download_bilibili_video
    from config import DOWNLOAD_DIR

    # 获取视频
    use_local = input("是否使用本地视频? (y/n): ").strip().lower()

    if use_local == "y":
        video_path = input("请输入视频文件路径: ").strip()
        if not os.path.isfile(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            sys.exit(1)
    else:
        video_url = input("请输入 B站视频链接: ").strip()
        video_path = download_bilibili_video(video_url, output_format='mp4', output_dir=DOWNLOAD_DIR)

    # 提取音频
    audio_path = extract_audio_from_video(video_path, output_format='mp3', output_dir=DOWNLOAD_DIR)

    # 选择配置
    file_type = input("字幕格式 (srt/cc) [默认 srt]: ").strip().lower() or 'srt'
    model = input("ASR 模型 (paraformer/sense_voice) [默认 paraformer]: ").strip().lower() or 'paraformer'
    segmenter = input("分段策略 (pause/llm) [默认 pause]: ").strip().lower() or 'pause'

    # 生成字幕
    subtitle_path = generate_subtitle_file(
        audio_path=audio_path,
        file_type=file_type,
        model=model,
        segmenter_type=segmenter
    )

    logger.info(f"字幕文件已生成: {subtitle_path}")

    # 硬编码（仅支持 SRT）
    if file_type == 'srt':
        encode = input("是否硬编码字幕到视频? (y/n): ").strip().lower()
        if encode == 'y':
            output_video = encode_subtitle_to_video(video_path, subtitle_path)
            logger.info(f"硬编码完成: {output_video}")
