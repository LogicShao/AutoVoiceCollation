"""
VAD 服务

基于 funasr fsmn-vad 的语音活动检测，仅用于切分时间戳。
强制使用 CPU 以节省 VRAM 给 LLM。
"""

from __future__ import annotations

from typing import Any

from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


class VADService:
    def __init__(
        self,
        min_segment_ms: int = 1000,
        max_segment_ms: int = 30000,
    ) -> None:
        self._min_segment_ms = int(min_segment_ms)
        self._max_segment_ms = int(max_segment_ms)
        self._model = self._load_model()

    @staticmethod
    def _load_model():
        try:
            from funasr import AutoModel
        except Exception as exc:
            raise RuntimeError("未能导入 funasr.AutoModel。请确认已安装 funasr 及其依赖。") from exc

        config = get_config()
        kwargs = {
            "model": "fsmn-vad",
            "device": "cpu",
            "disable_update": True,
            "model_hub": "huggingface",
            "cache_dir": str(config.paths.model_dir) if config.paths.model_dir else None,
        }
        logger.info("Loading fsmn-vad (CPU)...")
        return AutoModel(**kwargs)

    @staticmethod
    def _extract_segments(vad_output: Any) -> list[tuple[int, int]]:
        def _coerce_pairs(value: Any) -> list[tuple[int, int]]:
            pairs: list[tuple[int, int]] = []
            if not isinstance(value, list):
                return pairs
            for item in value:
                if (
                    isinstance(item, (list, tuple))
                    and len(item) >= 2
                    and isinstance(item[0], (int, float))
                    and isinstance(item[1], (int, float))
                ):
                    pairs.append((int(item[0]), int(item[1])))
            return pairs

        if isinstance(vad_output, dict):
            for key in ("value", "segments", "timestamp", "timestamps"):
                if key in vad_output:
                    pairs = _coerce_pairs(vad_output[key])
                    if pairs:
                        return pairs
            return []

        if isinstance(vad_output, list) and vad_output:
            first = vad_output[0]
            if isinstance(first, dict):
                return VADService._extract_segments(first)
            return _coerce_pairs(vad_output)

        return []

    def _normalize_segments(self, segments: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if not segments:
            return []

        cleaned: list[tuple[int, int]] = []
        for start_ms, end_ms in segments:
            start_ms = max(0, int(start_ms))
            end_ms = max(start_ms, int(end_ms))
            if end_ms == start_ms:
                continue
            cleaned.append((start_ms, end_ms))

        if not cleaned:
            return []

        cleaned.sort(key=lambda p: (p[0], p[1]))

        merged: list[tuple[int, int]] = []
        cur_start, cur_end = cleaned[0]
        for start_ms, end_ms in cleaned[1:]:
            cur_len = cur_end - cur_start
            if cur_len < self._min_segment_ms:
                cur_end = max(cur_end, end_ms)
                continue
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start_ms, end_ms
        merged.append((cur_start, cur_end))

        normalized: list[tuple[int, int]] = []
        for start_ms, end_ms in merged:
            length = end_ms - start_ms
            if length <= self._max_segment_ms:
                normalized.append((start_ms, end_ms))
                continue
            cursor = start_ms
            while cursor < end_ms:
                next_end = min(cursor + self._max_segment_ms, end_ms)
                normalized.append((cursor, next_end))
                cursor = next_end

        return normalized

    def segment_audio(self, audio_path: str) -> list[tuple[int, int]]:
        try:
            out = self._model.generate(input=audio_path)
        except Exception as exc:
            raise RuntimeError(f"VAD 推理失败: {exc}") from exc
        segments = self._extract_segments(out)
        return self._normalize_segments(segments)
