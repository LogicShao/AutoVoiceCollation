"""字幕分段器"""

from abc import ABC, abstractmethod

import jieba

from src.services.llm import LLMQueryParams, query_llm
from src.services.llm.prompts import get_prompt
from src.text_arrangement.split_text import smart_split
from src.utils.logging.logger import get_logger

from .config import SubtitleConfig
from .models import ASRResult, SubtitleSegment
from .utils import TextMatcher

logger = get_logger(__name__)


class SubtitleSegmenter(ABC):
    """字幕分段器抽象基类"""

    @abstractmethod
    def segment(self, asr_result: ASRResult) -> list[SubtitleSegment]:
        """将 ASR 结果分段为字幕片段"""
        pass


class PauseBasedSegmenter(SubtitleSegmenter):
    """基于停顿和语义的分段器"""

    def __init__(self, config: SubtitleConfig):
        self.config = config

    def segment(self, asr_result: ASRResult) -> list[SubtitleSegment]:
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
                    segments.append(
                        SubtitleSegment(text=current_text, start_time=current_start, end_time=end)
                    )
                    current_chars = []
                    current_text = ""

        # 处理剩余部分
        if current_chars:
            segments.append(
                SubtitleSegment(
                    text=current_text,
                    start_time=current_start,
                    end_time=current_chars[-1][2],
                )
            )

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
    STRONG_PUNCTUATION = "。？！；\n"
    # 中文标点符号（弱分段符号）
    WEAK_PUNCTUATION = "，、："

    def __init__(self, config: SubtitleConfig):
        self.config = config

    def segment(self, asr_result: ASRResult) -> list[SubtitleSegment]:
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
            is_weak_punctuation = (
                char in self.WEAK_PUNCTUATION and current_len >= min_segment_length
            )
            is_over_length = current_len >= self.config.max_chars_per_segment
            is_pause = (
                next_pause > self.config.pause_threshold and current_len >= min_segment_length
            )

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
                segments.append(
                    SubtitleSegment(
                        text=current_text.strip(),
                        start_time=current_start,
                        end_time=end,
                    )
                )
                current_chars = []
                current_text = ""

        # 处理剩余部分
        if current_chars:
            segments.append(
                SubtitleSegment(
                    text=current_text.strip(),
                    start_time=current_start,
                    end_time=current_chars[-1][2],
                )
            )

        logger.info(f"基于标点符号+停顿分段完成，共 {len(segments)} 个片段")
        return segments

    @staticmethod
    def _is_semantic_boundary(text: str) -> bool:
        """判断是否为语义边界"""
        words = list(jieba.cut(text))
        return len(words) > 1


class LLMBasedSegmenter(SubtitleSegmenter):
    """基于 LLM 的智能分段器"""

    def __init__(
        self,
        config: SubtitleConfig,
        api_server: str,
        fallback_segmenter: SubtitleSegmenter,
    ):
        self.config = config
        self.api_server = api_server
        self.fallback_segmenter = fallback_segmenter
        self.text_matcher = TextMatcher()

    def segment(self, asr_result: ASRResult) -> list[SubtitleSegment]:
        """使用 LLM 进行智能分段"""
        if not asr_result.timestamp:
            return []

        # 验证参数
        if self.config.llm_split_len > self.config.llm_max_tokens:
            raise ValueError(
                f"llm_split_len ({self.config.llm_split_len}) 不能超过 llm_max_tokens ({self.config.llm_max_tokens})"
            )

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
                logger.warning("LLM 分段失败，使用回退策略处理该块")
                # 找到该块对应的时间戳范围
                start_idx = time_cursor
                end_idx = time_cursor + len(chunk_clean)
                partial_result = ASRResult(
                    text=chunk_clean, timestamp=asr_result.timestamp[start_idx:end_idx]
                )
                fallback_segments = self.fallback_segmenter.segment(partial_result)
                segments.extend(fallback_segments)
                time_cursor = end_idx

        logger.info(f"LLM 分段完成，共 {len(segments)} 个片段")
        return segments

    def _segment_chunk(
        self,
        chunk: str,
        full_timestamp: list[tuple[str, float, float]],
        time_cursor: int,
    ) -> list[SubtitleSegment]:
        """
        使用 LLM 分段单个文本块

        Args:
            chunk: 要分段的文本块
            full_timestamp: 完整的时间戳数组
            time_cursor: 当前在时间戳数组中的位置
        """
        prompt_spec = getattr(self, "_segment_prompt_spec", None)
        if prompt_spec is None:
            prompt_spec = get_prompt("subtitle_segment")
            self._segment_prompt_spec = prompt_spec
        system_instruction = prompt_spec.render_system(
            max_chars_per_segment=self.config.max_chars_per_segment
        )
        user_content = prompt_spec.render_user(text=chunk)

        llm_params = LLMQueryParams(
            content=user_content,
            system_instruction=system_instruction,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
            api_server=self.api_server,
            top_p=self.config.llm_top_p,
            top_k=self.config.llm_top_k,
        )

        # 尝试多次查询
        for attempt in range(self.config.llm_retry):
            logger.info(
                f"LLM 查询尝试 {attempt + 1}/{self.config.llm_retry}，文本长度: {len(chunk)}"
            )

            try:
                response = query_llm(llm_params)
                response_clean = response.replace(" ", "").replace("\n", "")
                split_parts = response_clean.split("|")

                # 验证响应
                if self.text_matcher.is_similar(
                    "".join(split_parts), chunk, self.config.max_edit_distance
                ):
                    logger.info("LLM 分段成功")
                    return self._align_segments_with_timestamp(
                        split_parts, chunk, full_timestamp, time_cursor
                    )
                logger.warning(f"LLM 响应与原文不匹配，尝试 {attempt + 1}")

            except Exception as e:
                logger.error(f"LLM 查询出错: {e}")

        logger.warning(f"LLM 查询失败，已重试 {self.config.llm_retry} 次")
        return []

    def _align_segments_with_timestamp(
        self,
        split_parts: list[str],
        original_chunk: str,
        full_timestamp: list[tuple[str, float, float]],
        time_cursor: int,
    ) -> list[SubtitleSegment]:
        """将 LLM 切分的文本段与时间戳对齐"""
        # 修复切分结果
        aligned_parts = TextMatcher.align_text_segments(
            split_parts, original_chunk, self.config.max_edit_distance
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
                segments.append(
                    SubtitleSegment(
                        text=part,
                        start_time=part_chars[0][1],
                        end_time=part_chars[-1][2],
                    )
                )

        return segments
