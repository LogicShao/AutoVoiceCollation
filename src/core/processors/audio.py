"""
音频处理器

负责音频文件的ASR识别、LLM润色和输出生成
"""

import os
import json
import shutil
from typing import Optional, Any, Tuple

from src.Timer import Timer
from src.bilibili_downloader import BiliVideoFile, new_local_bili_file
from src.services.asr import transcribe_audio
from src.core.exceptions import TaskCancelledException
from src.text_arrangement.summary_by_llm import summarize_text
from src.text_arrangement.text_exporter import text_to_img_or_pdf

from .base import BaseProcessor

# 延迟导入配置，避免循环导入
import src.config as config


class AudioProcessor(BaseProcessor):
    """音频处理器"""

    def _validate_inputs(
        self,
        audio_file: BiliVideoFile,
        llm_api: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        """
        验证输入参数

        Args:
            audio_file: 音频文件对象
            llm_api: LLM API服务
            temperature: 温度参数
            max_tokens: 最大token数

        Raises:
            FileNotFoundError: 音频文件不存在
            ValueError: 参数无效
        """
        if not os.path.exists(audio_file.path):
            raise FileNotFoundError(f"Audio file not found: {audio_file.path}")

        if not 0 <= temperature <= 2:
            raise ValueError(f"Temperature must be between 0 and 2, got {temperature}")

        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")

        if llm_api not in config.LLM_SERVER_SUPPORTED:
            raise ValueError(
                f"Unsupported LLM API: {llm_api}. Supported: {config.LLM_SERVER_SUPPORTED}"
            )

    def _create_output_directory(self, audio_file: BiliVideoFile) -> str:
        """
        创建输出目录

        Args:
            audio_file: 音频文件对象

        Returns:
            str: 输出目录路径
        """
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

        audio_file_name = os.path.basename(audio_file.path).split(".")[0]
        output_dir = os.path.join(config.OUTPUT_DIR, audio_file_name)

        # 避免目录重复
        if os.path.exists(output_dir):
            suffix_id = 1
            while os.path.exists(f"{output_dir}_{suffix_id}"):
                suffix_id += 1
            output_dir = f"{output_dir}_{suffix_id}"

        os.makedirs(output_dir)

        # 保存视频信息
        info_file_path = os.path.join(output_dir, "video_info.txt")
        audio_file.save_in_json(info_file_path)

        return output_dir

    def _extract_text(
        self, audio_file: BiliVideoFile, output_dir: str, task_id: str
    ) -> Tuple[str, float]:
        """
        执行ASR文本提取

        Args:
            audio_file: 音频文件对象
            output_dir: 输出目录
            task_id: 任务ID

        Returns:
            Tuple[str, float]: (提取的文本, 提取时间)
        """
        timer = Timer()
        timer.start()

        audio_text = transcribe_audio(
            audio_path=audio_file.path, model_type=config.ASR_MODEL, task_id=task_id
        )

        # 保存原始文本
        text_file_path = os.path.join(output_dir, "audio_transcription.txt")
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(audio_text)

        extract_time = timer.stop()
        return audio_text, extract_time

    def _polish_text(
        self,
        audio_text: str,
        output_dir: str,
        audio_file: BiliVideoFile,
        llm_api: str,
        temperature: float,
        max_tokens: int,
        task_id: str,
    ) -> Tuple[str, float]:
        """
        执行LLM文本润色

        Args:
            audio_text: 原始文本
            output_dir: 输出目录
            audio_file: 音频文件对象
            llm_api: LLM API服务
            temperature: 温度参数
            max_tokens: 最大token数
            task_id: 任务ID

        Returns:
            Tuple[str, float]: (润色后的文本, 润色时间)
        """
        if config.DISABLE_LLM_POLISH:
            self.logger.info("LLM polish is disabled, skipping")
            return audio_text, 0.0

        # 延迟导入避免循环依赖
        from src.text_arrangement.polish_by_llm import polish_text

        timer = Timer()
        timer.start()

        polished_text = polish_text(
            audio_text,
            api_service=llm_api,
            split_len=round(max_tokens * 0.7),
            temperature=temperature,
            max_tokens=max_tokens,
            debug_flag=config.DEBUG_FLAG,
            async_flag=config.ASYNC_FLAG,
            task_id=task_id,
        )

        # 保存润色后的文本
        polish_text_file_path = os.path.join(output_dir, "polish_text.txt")
        audio_file.save_in_text(
            polished_text, llm_api, temperature, config.ASR_MODEL, polish_text_file_path
        )

        polish_time = timer.stop()
        return polished_text, polish_time

    def _generate_summary(self, polished_text: str, output_dir: str, title: str) -> str:
        """
        生成文本摘要

        Args:
            polished_text: 润色后的文本
            output_dir: 输出目录
            title: 标题

        Returns:
            str: 摘要文本
        """
        if config.DISABLE_LLM_SUMMARY:
            self.logger.info("LLM summary is disabled, skipping")
            return ""

        summary_text = summarize_text(
            txt=polished_text,
            api_server=config.SUMMARY_LLM_SERVER,
            temperature=config.SUMMARY_LLM_TEMPERATURE,
            max_tokens=config.SUMMARY_LLM_MAX_TOKENS,
            title=title,
        )

        # 保存摘要
        md_file_path = os.path.join(output_dir, "summary_text.md")
        with open(md_file_path, "w", encoding="utf-8") as f:
            f.write(summary_text)

        self.logger.info(f"Summary text saved to {md_file_path}")
        return summary_text

    def _export_output(
        self,
        polished_text: str,
        output_dir: str,
        title: str,
        llm_api: str,
        temperature: float,
    ) -> None:
        """
        导出输出文件(PDF/图片)

        Args:
            polished_text: 润色后的文本
            output_dir: 输出目录
            title: 标题
            llm_api: LLM API服务
            temperature: 温度参数
        """
        text_to_img_or_pdf(
            polished_text,
            title=title,
            output_style=config.OUTPUT_STYLE,
            output_path=output_dir,
            LLM_info=f"({llm_api},温度:{temperature})",
            ASR_model=config.ASR_MODEL,
        )

    def _zip_output(self, output_dir: str) -> Optional[str]:
        """
        压缩输出目录

        Args:
            output_dir: 输出目录

        Returns:
            Optional[str]: ZIP文件路径或None
        """
        if not config.ZIP_OUTPUT_ENABLED:
            return None

        zip_path = f"{output_dir}.zip"
        shutil.make_archive(base_name=output_dir, format="zip", root_dir=output_dir)
        return zip_path

    def process(
        self,
        audio_file: BiliVideoFile,
        llm_api: str,
        temperature: float,
        max_tokens: int,
        text_only: bool = False,
        task_id: Optional[str] = None,
    ) -> Tuple[Any, float, float, Optional[str]]:
        """
        处理音频文件，提取文本并润色

        Args:
            audio_file: 音频文件对象
            llm_api: LLM API服务
            temperature: 温度参数
            max_tokens: 最大token数
            text_only: 是否只返回纯文本结果（不生成PDF）
            task_id: 任务ID，用于终止控制

        Returns:
            Tuple[Any, float, float, Optional[str]]: (结果数据, 提取时间, 润色时间, ZIP文件路径)
                - text_only=True: 返回字典数据
                - text_only=False: 返回字典数据
        """
        task_id = self._ensure_task(task_id)

        try:
            # 输入验证
            self._validate_inputs(audio_file, llm_api, temperature, max_tokens)
            self._check_cancellation(task_id)

            # 创建输出目录
            output_dir = self._create_output_directory(audio_file)
            self._check_cancellation(task_id)

            # ASR 提取文本
            audio_text, extract_time = self._extract_text(
                audio_file, output_dir, task_id
            )
            self._check_cancellation(task_id)

            # LLM 润色文本
            polished_text, polish_time = self._polish_text(
                audio_text,
                output_dir,
                audio_file,
                llm_api,
                temperature,
                max_tokens,
                task_id,
            )
            self._check_cancellation(task_id)

            # 纯文本模式
            if text_only:
                result_data = {
                    "title": audio_file.title,
                    "audio_file": audio_file.path,
                    "asr_model": config.ASR_MODEL,
                    "llm_api": llm_api,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "extract_time": extract_time,
                    "polish_time": polish_time,
                    "audio_text": audio_text,
                    "polished_text": polished_text,
                    "summary_text": None,
                    "output_dir": output_dir,
                }

                # 保存为JSON
                json_file_path = os.path.join(output_dir, "result.json")
                with open(json_file_path, "w", encoding="utf-8") as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)

                self.logger.info(f"Text-only result saved to {json_file_path}")
                self.logger.info("all done")
                return result_data, extract_time, polish_time, None

            # 正常模式：生成PDF/图片
            self._export_output(
                polished_text, output_dir, audio_file.title, llm_api, temperature
            )
            self._check_cancellation(task_id)

            # 生成摘要
            summary_text = self._generate_summary(
                polished_text, output_dir, audio_file.title
            )
            self._check_cancellation(task_id)

            # 压缩输出
            zip_file = self._zip_output(output_dir)
            self.logger.info("all done")

            # 构建返回数据
            result_data = {
                "title": audio_file.title,
                "output_dir": output_dir,
                "audio_text": audio_text,
                "polished_text": polished_text,
                "summary_text": summary_text,
            }
            return result_data, extract_time, polish_time, zip_file

        except TaskCancelledException as e:
            self.logger.warning(f"Task cancelled: {e}")
            return f"任务已取消: {task_id}", 0, 0, None
        finally:
            self._cleanup_task(task_id)

    def process_uploaded_audio(
        self,
        audio_path: str,
        llm_api: str,
        temperature: float,
        max_tokens: int,
        text_only: bool = False,
        task_id: Optional[str] = None,
    ) -> Tuple[Any, float, float, Optional[str]]:
        """
        处理上传的音频文件

        Args:
            audio_path: 音频文件路径
            llm_api: LLM API服务
            temperature: 温度参数
            max_tokens: 最大token数
            text_only: 是否只返回纯文本结果
            task_id: 任务ID

        Returns:
            Tuple: (结果数据, 提取时间, 润色时间, ZIP文件路径)
        """
        if audio_path is None:
            return "请上传一个音频文件。", None, None, None

        audio_file = new_local_bili_file(audio_path)
        return self.process(
            audio_file, llm_api, temperature, max_tokens, text_only, task_id
        )
