"""
视频处理器

负责B站视频下载和批量处理
"""

from typing import Optional, Tuple, Any

from src.utils.helpers.timer import Timer
from src.bilibili_downloader import download_bilibili_audio, BiliVideoFile
from src.core.exceptions import TaskCancelledException

from .base import BaseProcessor
from .audio import AudioProcessor

# 导入配置系统
from src.utils.config import get_config


class VideoProcessor(BaseProcessor):
    """视频处理器"""

    def __init__(self):
        super().__init__()
        self.audio_processor = AudioProcessor()
        self.config = get_config()

    def process(
        self,
        video_url: str,
        llm_api: str,
        temperature: float,
        max_tokens: int,
        text_only: bool = False,
        task_id: Optional[str] = None,
    ) -> Tuple[Any, float, float, Optional[str]]:
        """
        下载并处理B站视频

        Args:
            video_url: B站视频URL
            llm_api: LLM API服务
            temperature: 温度参数
            max_tokens: 最大token数
            text_only: 是否只返回纯文本结果
            task_id: 任务ID

        Returns:
            Tuple[Any, float, float, Optional[str]]: (结果数据, 总提取时间, 润色时间, ZIP文件路径)
        """
        task_id = self._ensure_task(task_id)

        try:
            # 输入验证
            if not video_url or not video_url.startswith("http"):
                return "请输入正确的B站链接。", None, None, None

            self._check_cancellation(task_id)

            # 下载视频音频
            timer = Timer()
            timer.start()
            audio_file: BiliVideoFile = download_bilibili_audio(
                video_url, output_format="mp3", output_dir=str(self.config.paths.download_dir)
            )
            download_time = timer.stop()

            self._check_cancellation(task_id)

            # 处理音频
            output_dir, extract_time, polish_time, zip_file = (
                self.audio_processor.process(
                    audio_file, llm_api, temperature, max_tokens, text_only, task_id
                )
            )

            # 返回总时间（下载+提取）
            return output_dir, extract_time + download_time, polish_time, zip_file

        except TaskCancelledException as e:
            self.logger.warning(f"Task cancelled: {e}")
            return f"任务已取消: {task_id}", 0, 0, None
        finally:
            self._cleanup_task(task_id)

    def process_batch(
        self,
        urls: str,
        llm_api: str,
        temperature: float,
        max_tokens: int,
        text_only: bool = False,
        task_id: Optional[str] = None,
    ) -> Tuple[str, float, float, None]:
        """
        批量处理B站视频链接

        Args:
            urls: 多个URL，用换行符分隔
            llm_api: LLM API服务
            temperature: 温度参数
            max_tokens: 最大token数
            text_only: 是否只返回纯文本结果
            task_id: 任务ID

        Returns:
            Tuple[str, float, float, None]: (输出目录列表, 总提取时间, 总润色时间, None)
        """
        task_id = self._ensure_task(task_id)

        try:
            # 输入验证
            if not urls or not urls.strip():
                raise ValueError("URLs cannot be empty")

            url_list = urls.strip().split("\n")
            all_output_dirs = []
            total_extract_time = 0.0
            total_polish_time = 0.0

            for url in url_list:
                url = url.strip()
                if not url:
                    continue

                self._check_cancellation(task_id)

                if url.startswith("http"):
                    # 下载视频
                    timer = Timer()
                    timer.start()
                    audio_file = download_bilibili_audio(
                        url, output_format="mp3", output_dir=str(self.config.paths.download_dir)
                    )
                    download_time = timer.stop()

                    self._check_cancellation(task_id)

                    # 处理音频
                    result_data, extract_time, polish_time, zip_file = (
                        self.audio_processor.process(
                            audio_file,
                            llm_api,
                            temperature,
                            max_tokens,
                            text_only,
                            task_id,
                        )
                    )

                    # 处理返回结果（可能是字典或字符串）
                    if isinstance(result_data, dict):
                        output_dir = result_data.get("output_dir", "")
                        if self.config.zip_output_enabled and zip_file:
                            all_output_dirs.append(zip_file)
                        else:
                            all_output_dirs.append(output_dir)
                    else:
                        # 错误情况（如任务取消），result_data 是字符串
                        all_output_dirs.append(str(result_data))

                    total_extract_time += extract_time + download_time
                    total_polish_time += polish_time
                else:
                    raise ValueError(f"Invalid URL: {url}")

            # 过滤空字符串，并确保所有元素都是字符串
            valid_output_dirs = [str(d) for d in all_output_dirs if d]
            return (
                "\n".join(valid_output_dirs),
                total_extract_time,
                total_polish_time,
                None,
            )

        except TaskCancelledException as e:
            self.logger.warning(f"Batch task cancelled: {e}")
            return f"批量任务已取消: {task_id}", 0, 0, None
        finally:
            self._cleanup_task(task_id)
