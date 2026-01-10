"""
字幕处理器

负责视频字幕生成和硬编码
"""

import os

from src.core.exceptions import TaskCancelledException
from src.services.download.bilibili_downloader import extract_audio_from_video
from src.services.subtitle import (
    SubtitleConfig,
    encode_subtitle_to_video,
    gen_timestamped_text_file,
    generate_subtitle_file,
    hard_encode_dot_srt_file,
)

from .base import BaseProcessor

# 延迟导入配置，避免循环导入


class SubtitleProcessor(BaseProcessor):
    """字幕处理器"""

    def process_simple(self, video_file: str) -> tuple[str, str]:
        """
        生成视频字幕并硬编码到视频

        Args:
            video_file: 视频文件路径

        Returns:
            Tuple[str, str]: (字幕文件路径, 输出视频路径)

        Raises:
            FileNotFoundError: 视频文件不存在
        """
        if not video_file or not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file not found: {video_file}")

        audio_file = extract_audio_from_video(video_file)
        srt_file = gen_timestamped_text_file(audio_file)
        output_file = hard_encode_dot_srt_file(video_file, srt_file)
        return srt_file, output_file

    def process(
        self,
        media_file: str,
        file_type: str = "srt",
        model: str = "paraformer",
        segmenter_type: str = "pause",
        output_type: str = "subtitle_only",
        api_server: str | None = None,
        pause_threshold: float = 0.6,
        max_chars: int = 16,
        batch_size_s: int = 5,
        paraformer_chunk_size_s: int = 30,
        task_id: str | None = None,
    ) -> tuple[str | None, str | None, str]:
        """
        增强版字幕生成函数，支持更多配置选项

        Args:
            media_file: 媒体文件路径（音频或视频）
            file_type: 字幕格式 ('srt' 或 'cc')
            model: ASR 模型 ('paraformer' 或 'sense_voice')
            segmenter_type: 分段策略 ('pause' 或 'llm')
            output_type: 输出类型
                - 'subtitle_only': 仅生成字幕文件
                - 'video_with_subtitle': 生成字幕文件 + 硬编码到视频
            api_server: LLM API 服务器（segmenter_type='llm' 时使用）
            pause_threshold: 停顿阈值（秒）
            max_chars: 每段最大字符数
            batch_size_s: SenseVoice 批处理大小（秒）
            paraformer_chunk_size_s: Paraformer 分块大小（秒）
            task_id: 任务ID，用于终止控制

        Returns:
            Tuple[Optional[str], Optional[str], str]: (字幕文件路径, 带字幕视频路径或None, 处理信息)
        """
        task_id = self._ensure_task(task_id)

        try:
            self.logger.info(f"开始生成字幕，任务ID: {task_id}")

            # 验证输入文件
            if not media_file or not os.path.exists(media_file):
                raise FileNotFoundError(f"媒体文件不存在: {media_file}")

            self._check_cancellation(task_id)

            # 判断文件类型
            file_ext = os.path.splitext(media_file)[1].lower()
            is_video = file_ext in [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"]
            is_audio = file_ext in [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"]

            if not is_video and not is_audio:
                raise ValueError(f"不支持的文件格式: {file_ext}")

            # 提取音频（如果是视频）
            if is_video:
                self.logger.info("检测到视频文件，正在提取音频...")
                audio_file = extract_audio_from_video(media_file)
            else:
                self.logger.info("检测到音频文件，直接使用")
                audio_file = media_file

            self._check_cancellation(task_id)

            # 创建字幕配置
            config = SubtitleConfig(
                pause_threshold=pause_threshold,
                max_chars_per_segment=max_chars,
                batch_size_s=batch_size_s,
                paraformer_chunk_size_s=paraformer_chunk_size_s,
            )

            # 设置 LLM API 服务器（如果使用 LLM 分段）
            if segmenter_type == "llm":
                if api_server is None:
                    api_server = config.LLM_SERVER  # 使用配置中的默认值
                self.logger.info(f"使用 LLM 分段策略，API 服务器: {api_server}")
            else:
                api_server = "gemini-2.0-flash"  # 默认值（不会被使用）

            self._check_cancellation(task_id)

            # 生成字幕文件
            self.logger.info(
                f"生成字幕文件，格式: {file_type}, 模型: {model}, 分段策略: {segmenter_type}"
            )
            subtitle_path = generate_subtitle_file(
                audio_path=audio_file,
                file_type=file_type,
                model=model,
                segmenter_type=segmenter_type,
                config=config,
                api_server=api_server,
                paraformer_chunk_size_s=paraformer_chunk_size_s,
            )

            self._check_cancellation(task_id)

            # 硬编码字幕到视频（如果需要）
            video_with_subtitle = None
            if output_type == "video_with_subtitle":
                if not is_video:
                    info_msg = "警告: 输入为音频文件，无法生成带字幕的视频。仅返回字幕文件。"
                    self.logger.warning(info_msg)
                elif file_type != "srt":
                    info_msg = "警告: 硬编码仅支持 SRT 格式，将跳过视频生成。"
                    self.logger.warning(info_msg)
                else:
                    self.logger.info("正在硬编码字幕到视频...")
                    video_with_subtitle = encode_subtitle_to_video(
                        video_path=media_file, srt_path=subtitle_path
                    )

            self._check_cancellation(task_id)

            # 构建返回信息
            info_lines = [
                f"✅ 字幕文件已生成: {subtitle_path}",
                f"   - 格式: {file_type.upper()}",
                f"   - ASR 模型: {model}",
                f"   - 分段策略: {segmenter_type}",
            ]

            if video_with_subtitle:
                info_lines.append(f"✅ 带字幕视频已生成: {video_with_subtitle}")

            info_msg = "\n".join(info_lines)
            self.logger.info(f"字幕生成完成: {task_id}")

            return subtitle_path, video_with_subtitle, info_msg

        except TaskCancelledException as e:
            self.logger.warning(f"字幕生成任务已取消: {e}")
            return None, None, f"任务已取消: {task_id}"
        except Exception as e:
            self.logger.error(f"字幕生成失败: {e}", exc_info=True)
            return None, None, f"❌ 生成失败: {str(e)}"
        finally:
            self._cleanup_task(task_id)
