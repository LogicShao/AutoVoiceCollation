"""字幕生成配置"""

from dataclasses import dataclass
from pathlib import Path


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
