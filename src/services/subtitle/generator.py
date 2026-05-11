import os
import subprocess
from pathlib import Path

from src.utils.logging.logger import get_logger

from .asr_processor import ParaformerProcessor, SenseVoiceProcessor
from .config import SubtitleConfig
from .models import SubtitleSegment
from .segmenter import LLMBasedSegmenter, PauseBasedSegmenter, PunctuationPauseSegmenter
from .utils import PathHelper, TimestampFormatter

logger = get_logger(__name__)


# ============================================================================
# 字幕文件生成器
# ============================================================================


class SubtitleFileGenerator:
    """字幕文件生成器"""

    @staticmethod
    def generate_srt(segments: list[SubtitleSegment], output_path: str) -> str:
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
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(content)

        logger.info(f"SRT 字幕文件已生成: {output_path}")
        return output_path

    @staticmethod
    def generate_cc(segments: list[SubtitleSegment], output_path: str) -> str:
        """生成 CC 字幕文件"""
        lines = []
        for seg in segments:
            start_ts = TimestampFormatter.to_cc(seg.start_time)
            end_ts = TimestampFormatter.to_cc(seg.end_time)
            lines.append(f"{start_ts} {end_ts} {seg.text.strip()}")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(content)

        logger.info(f"CC 字幕文件已生成: {output_path}")
        return output_path


# ============================================================================
# 视频硬编码器
# ============================================================================


class SubtitleVideoEncoder:
    """字幕视频硬编码器"""

    @staticmethod
    def encode(video_path: str, srt_path: str, output_path: str | None = None) -> str:
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
            "ffmpeg",
            "-i",
            video_ffmpeg,
            "-vf",
            f"subtitles={srt_ffmpeg}",
            "-c:a",
            "copy",
            "-y",  # 覆盖已存在的文件
            output_ffmpeg,
        ]

        logger.info(f"开始硬编码字幕: {output_path}")
        logger.debug(f"FFmpeg 命令: {' '.join(command)}")

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=300,
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
    output_path: str | None = None,
    file_type: str = "srt",
    model: str = "paraformer",
    segmenter_type: str = "pause",
    config: SubtitleConfig | None = None,
    api_server: str = "gemini-2.0-flash",
    paraformer_chunk_size_s: int = 30,
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

    if file_type not in ["srt", "cc"]:
        raise ValueError(f"不支持的字幕格式: {file_type}")

    # 使用默认配置或更新配置
    if config is None:
        from src.utils.config import get_config

        app_config = get_config()
        temp_dir = app_config.paths.temp_dir or Path("./temp")
        config = SubtitleConfig(temp_dir=temp_dir)

    # 更新 Paraformer 分块大小
    config.paraformer_chunk_size_s = paraformer_chunk_size_s

    # 确定输出路径
    if output_path is None:
        base_name = os.path.splitext(audio_path)[0]
        output_path = f"{base_name}.{file_type}"

    # 1. ASR 识别
    logger.info(f"使用 {model} 模型进行语音识别")
    if model == "sense_voice":
        asr_processor = SenseVoiceProcessor(config)
    elif model == "paraformer":
        asr_processor = ParaformerProcessor(config)
    else:
        raise ValueError(f"不支持的 ASR 模型: {model}")

    asr_result = asr_processor.process(audio_path)

    # 2. 字幕分段
    logger.info(f"使用 {segmenter_type} 策略进行字幕分段")
    if segmenter_type == "pause":
        segmenter = PauseBasedSegmenter(config)
    elif segmenter_type == "punctuation":
        segmenter = PunctuationPauseSegmenter(config)
    elif segmenter_type == "llm":
        fallback = PunctuationPauseSegmenter(config)  # 使用标点分段作为回退策略
        segmenter = LLMBasedSegmenter(config, api_server, fallback)
    else:
        raise ValueError(f"不支持的分段策略: {segmenter_type}")

    segments = segmenter.segment(asr_result)

    if not segments:
        raise ValueError("未能生成任何字幕片段")

    # 3. 生成字幕文件
    logger.info(f"生成 {file_type.upper()} 字幕文件")
    if file_type == "srt":
        return SubtitleFileGenerator.generate_srt(segments, output_path)
    return SubtitleFileGenerator.generate_cc(segments, output_path)


def encode_subtitle_to_video(video_path: str, srt_path: str, output_path: str | None = None) -> str:
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
# CLI 入口
# ============================================================================

if __name__ == "__main__":
    import sys

    from src.services.download import (
        download_bilibili_video,
        extract_audio_from_video,
    )
    from src.utils.config import get_config

    config = get_config()

    # 获取视频
    use_local = input("是否使用本地视频? (y/n): ").strip().lower()

    if use_local == "y":
        video_path = input("请输入视频文件路径: ").strip()
        if not os.path.isfile(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            sys.exit(1)
    else:
        video_url = input("请输入 B站视频链接: ").strip()
        video_path = download_bilibili_video(
            video_url, output_format="mp4", output_dir=str(config.paths.download_dir)
        )

    # 提取音频
    audio_path = extract_audio_from_video(
        video_path, output_format="mp3", output_dir=str(config.paths.download_dir)
    )

    # 选择配置
    file_type = input("字幕格式 (srt/cc) [默认 srt]: ").strip().lower() or "srt"
    model = (
        input("ASR 模型 (paraformer/sense_voice) [默认 paraformer]: ").strip().lower()
        or "paraformer"
    )
    segmenter = input("分段策略 (pause/llm) [默认 pause]: ").strip().lower() or "pause"

    # 生成字幕
    subtitle_path = generate_subtitle_file(
        audio_path=audio_path, file_type=file_type, model=model, segmenter_type=segmenter
    )

    logger.info(f"字幕文件已生成: {subtitle_path}")

    # 硬编码（仅支持 SRT）
    if file_type == "srt":
        encode = input("是否硬编码字幕到视频? (y/n): ").strip().lower()
        if encode == "y":
            output_video = encode_subtitle_to_video(video_path, subtitle_path)
            logger.info(f"硬编码完成: {output_video}")
