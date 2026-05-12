"""结构化视频分析服务"""

from .generator import VideoAnalysis, VideoSegment, generate_analysis

__all__ = ["VideoAnalysis", "VideoSegment", "generate_analysis"]
