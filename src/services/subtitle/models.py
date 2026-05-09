"""字幕数据模型"""

from dataclasses import dataclass

from src.text_arrangement.split_text import clean_asr_text


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
    timestamp: list[tuple[str, float, float]]  # [(字符, 开始时间, 结束时间), ...]

    def get_clean_text(self) -> str:
        """获取清理后的文本"""
        return clean_asr_text(self.text)
