"""
音频处理器

负责音频文件的ASR识别、LLM润色和输出生成
"""

import json
import os
import shutil
from typing import Any

from src.core.exceptions import TaskCancelledException
from src.services.asr import transcribe_audio
from src.services.download.bilibili_downloader import BiliVideoFile, new_local_bili_file
from src.text_arrangement.summary_by_llm import summarize_text
from src.text_arrangement.text_exporter import text_to_img_or_pdf

# 导入配置系统
from src.utils.config import get_config
from src.utils.helpers.timer import Timer

from .base import BaseProcessor


class AudioProcessor(BaseProcessor):
    """音频处理器"""

    def __init__(self):
        super().__init__()
        self.config = get_config()

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

        if llm_api not in self.config.llm.llm_server_supported:
            raise ValueError(
                f"Unsupported LLM API: {llm_api}. Supported: {self.config.llm.llm_server_supported}"
            )

    def _create_output_directory(self, audio_file: BiliVideoFile) -> str:
        """
        创建输出目录

        Args:
            audio_file: 音频文件对象

        Returns:
            str: 输出目录路径
        """
        self.config.paths.output_dir.mkdir(parents=True, exist_ok=True)
        self.config.paths.download_dir.mkdir(parents=True, exist_ok=True)

        audio_file_name = os.path.basename(audio_file.path).split(".")[0]
        output_dir = self.config.paths.output_dir / audio_file_name

        # 避免目录重复
        if output_dir.exists():
            suffix_id = 1
            while (self.config.paths.output_dir / f"{audio_file_name}_{suffix_id}").exists():
                suffix_id += 1
            output_dir = self.config.paths.output_dir / f"{audio_file_name}_{suffix_id}"

        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存视频信息
        info_file_path = output_dir / "video_info.txt"
        audio_file.save_in_json(str(info_file_path))

        return str(output_dir)

    def _extract_text(
        self, audio_file: BiliVideoFile, output_dir: str, task_id: str
    ) -> tuple[str, float]:
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
            audio_path=audio_file.path,
            model_type=self.config.asr.asr_model,
            task_id=task_id,
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
    ) -> tuple[str, float]:
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
        if self.config.llm.disable_llm_polish:
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
            debug_flag=self.config.debug_flag,
            async_flag=self.config.llm.async_flag,
            task_id=task_id,
        )

        # 保存润色后的文本
        polish_text_file_path = os.path.join(output_dir, "polish_text.txt")
        audio_file.save_in_text(
            polished_text,
            llm_api,
            temperature,
            self.config.asr.asr_model,
            polish_text_file_path,
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
        if self.config.llm.disable_llm_summary:
            self.logger.info("LLM summary is disabled, skipping")
            return ""

        summary_text = summarize_text(
            txt=polished_text,
            api_server=self.config.llm.summary_llm_server,
            temperature=self.config.llm.summary_llm_temperature,
            max_tokens=self.config.llm.summary_llm_max_tokens,
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
        pdf_filename: str | None = None,
    ) -> None:
        """
        导出输出文件(PDF/图片)

        Args:
            polished_text: 润色后的文本
            output_dir: 输出目录
            title: 标题
            llm_api: LLM API服务
            temperature: 温度参数
            pdf_filename: PDF 文件名（不含扩展名），用于智能命名
        """
        text_to_img_or_pdf(
            polished_text,
            title=title,
            output_style=self.config.output_style,
            output_path=output_dir,
            LLM_info=f"({llm_api},温度:{temperature})",
            ASR_model=self.config.asr.asr_model,
            pdf_filename=pdf_filename,
        )

    def _zip_output(self, output_dir: str) -> str | None:
        """
        压缩输出目录

        Args:
            output_dir: 输出目录

        Returns:
            Optional[str]: ZIP文件路径或None
        """
        if not self.config.zip_output_enabled:
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
        task_id: str | None = None,
    ) -> tuple[Any, float, float, str | None]:
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
            audio_text, extract_time = self._extract_text(audio_file, output_dir, task_id)
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
                    "asr_model": self.config.asr.asr_model,
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

            # ✨ 生成智能 PDF 文件名
            pdf_filename = None
            if audio_file.title:
                # B站视频：直接使用标题
                pdf_filename = audio_file.title
                self.logger.info(f"使用视频标题作为文件名: {pdf_filename}")
            else:
                # 本地文件：尝试通过 LLM 生成标题
                self.logger.info("本地文件无标题，尝试通过 LLM 生成...")
                try:
                    from src.utils.helpers.filename import generate_title_from_text

                    # 同步调用（不再需要 asyncio）
                    generated_title = generate_title_from_text(
                        text=audio_text,  # 使用原始转录文本
                        llm_service=llm_api,
                        max_length=50,
                    )
                    if generated_title:
                        pdf_filename = generated_title
                        # 更新 audio_file.title 以便其他地方使用
                        audio_file.title = generated_title
                        self.logger.info(f"LLM 生成标题成功: {generated_title}")
                    else:
                        self.logger.warning("LLM 标题生成失败，使用默认文件名")
                except Exception as e:
                    self.logger.error(f"标题生成异常: {e}", exc_info=True)
                    # 失败时不影响主流程，pdf_filename 保持为 None

            # 正常模式：生成PDF/图片
            self._export_output(
                polished_text,
                output_dir,
                audio_file.title or "未命名",
                llm_api,
                temperature,
                pdf_filename=pdf_filename,
            )
            self._check_cancellation(task_id)

            # 生成摘要
            summary_text = self._generate_summary(polished_text, output_dir, audio_file.title)
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
        task_id: str | None = None,
    ) -> tuple[Any, float, float, str | None]:
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
        return self.process(audio_file, llm_api, temperature, max_tokens, text_only, task_id)
