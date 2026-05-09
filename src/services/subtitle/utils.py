"""字幕生成工具类"""

import difflib
from datetime import timedelta
from pathlib import Path

from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


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
                        dp[i - 1][j - 1] + 1,  # 替换
                    )
        return dp[len_s1][len_s2]

    @staticmethod
    def is_similar(s1: str, s2: str, max_distance: int) -> bool:
        """判断两个字符串是否相似"""
        return TextMatcher.levenshtein_distance(s1, s2) <= max_distance

    @staticmethod
    def align_text_segments(segments: list[str], original: str, max_distance: int) -> list[str]:
        """
        将 LLM 切分的文本段与原始文本对齐

        原理：使用序列匹配算法在原文中查找每个段落的最佳匹配位置
        """
        processed = "".join(segments)
        if not TextMatcher.is_similar(processed, original, max_distance):
            logger.warning("切分文本与原文差异过大，放弃对齐")
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
        self._created_files: list[Path] = []

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
