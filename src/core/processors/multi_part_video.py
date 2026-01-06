"""
多P视频处理器

负责B站多P（多分集）视频的下载、处理和合并
"""

from typing import List, Optional, Tuple, Any
from pathlib import Path

from .base import BaseProcessor
from .audio import AudioProcessor
from src.services.download import download_bilibili_audio, get_multi_part_info
from src.core.exceptions import TaskCancelledException
from src.utils.config import get_config
from src.utils.helpers.timer import Timer


class MultiPartVideoProcessor(BaseProcessor):
    """多P视频处理器"""

    def __init__(self):
        super().__init__()
        self.audio_processor = AudioProcessor()
        self.config = get_config()

    def process(
        self,
        video_url: str,
        selected_parts: List[int],
        llm_api: str,
        temperature: float,
        max_tokens: int,
        text_only: bool = False,
        task_id: Optional[str] = None,
    ) -> Tuple[Any, float, float, Optional[str]]:
        """
        处理多P视频

        Args:
            video_url: B站视频URL
            selected_parts: 选中的分P编号列表（从1开始）
            llm_api: LLM API服务
            temperature: 温度参数
            max_tokens: 最大token数
            text_only: 是否只返回纯文本结果
            task_id: 任务ID

        Returns:
            Tuple[Any, float, float, Optional[str]]: (结果数据, 总提取时间, 总润色时间, ZIP文件路径)
        """
        task_id = self._ensure_task(task_id)

        try:
            # 1. 获取多P信息并验证
            self.logger.info(f"获取多P视频信息：{video_url}")
            multi_part_info = get_multi_part_info(video_url)
            if not multi_part_info:
                raise ValueError("非多P视频或获取信息失败")

            # 验证选中的分P编号
            if not selected_parts:
                raise ValueError("未选择任何分P")

            selected_parts_info = multi_part_info.get_selected_parts(selected_parts)
            if not selected_parts_info:
                raise ValueError(f"无效的分P编号：{selected_parts}")

            self.logger.info(f"多P视频：{multi_part_info.main_title}, 选中 {len(selected_parts_info)} 个分P")
            self._check_cancellation(task_id)

            # 2. 创建输出目录
            output_dir = self.audio_processor._create_output_directory(
                multi_part_info.main_title
            )
            parts_dir = Path(output_dir) / "parts"
            parts_dir.mkdir(exist_ok=True)

            self.logger.info(f"输出目录：{output_dir}")

            # 3. 依次处理各分P
            part_results = []
            total_extract_time = 0.0
            total_polish_time = 0.0
            failed_parts = []

            for idx, part_info in enumerate(selected_parts_info, start=1):
                self._check_cancellation(task_id)  # ✅ 每个分P前检查取消

                try:
                    self.logger.info(f"处理分P {part_info.part_number}/{len(selected_parts_info)}: {part_info.title}")
                    result = self._process_single_part(
                        part_info, parts_dir, llm_api, temperature, max_tokens, task_id
                    )
                    part_results.append(result)
                    total_extract_time += result["extract_time"]
                    total_polish_time += result["polish_time"]
                    self.logger.info(f"分P {part_info.part_number} 处理完成")

                except TaskCancelledException:
                    # 任务取消异常需要向上传播
                    raise

                except Exception as e:
                    self.logger.error(f"处理分P {part_info.part_number} 失败: {e}", exc_info=True)
                    failed_parts.append({
                        "part_number": part_info.part_number,
                        "title": part_info.title,
                        "error": str(e)
                    })
                    # 跳过失败的分P，继续处理其他分P
                    continue

            if not part_results:
                raise RuntimeError("所有分P处理均失败")

            self._check_cancellation(task_id)

            # 4. 合并文本（添加章节标题）
            self.logger.info("合并分P文本...")
            merged_polished_text = self._merge_parts_text(part_results, output_dir)

            self._check_cancellation(task_id)

            # 5. 生成摘要（可选）
            summary_text = None
            if not self.config.disable_llm_summary:
                self.logger.info("生成摘要...")
                summary_text = self.audio_processor._generate_summary(
                    merged_polished_text, llm_api, task_id
                )

            self._check_cancellation(task_id)

            # 6. 导出PDF/图片
            self.logger.info("导出最终结果...")
            self.audio_processor._export_output(merged_polished_text, output_dir, task_id)

            self._check_cancellation(task_id)

            # 7. 打包ZIP（可选）
            zip_file = None
            if self.config.zip_output_enabled:
                self.logger.info("打包ZIP文件...")
                zip_file = self.audio_processor._zip_output(output_dir)

            # 8. 构造返回结果
            result_data = {
                "title": multi_part_info.main_title,
                "output_dir": output_dir,
                "total_parts": len(selected_parts_info),
                "processed_parts": len(part_results),
                "polished_text": merged_polished_text,
                "summary_text": summary_text,
            }

            # 如果有失败的分P，添加失败信息
            if failed_parts:
                result_data["failed_parts"] = failed_parts
                result_data["message"] = f"部分分P处理失败 ({len(failed_parts)}/{len(selected_parts_info)})"
                self.logger.warning(f"部分分P处理失败：{failed_parts}")

            self.logger.info(f"多P视频处理完成，成功 {len(part_results)}/{len(selected_parts_info)} 个分P")
            return result_data, total_extract_time, total_polish_time, zip_file

        except TaskCancelledException as e:
            self.logger.warning(f"多P任务已取消: {e}")
            return f"任务已取消: {task_id}", 0, 0, None
        except Exception as e:
            self.logger.error(f"多P任务失败: {e}", exc_info=True)
            raise
        finally:
            self._cleanup_task(task_id)

    def _process_single_part(
        self,
        part_info,  # BiliVideoPart
        parts_dir: Path,
        llm_api: str,
        temperature: float,
        max_tokens: int,
        task_id: Optional[str],
    ) -> dict:
        """
        处理单个分P（复用 AudioProcessor 逻辑）

        Args:
            part_info: 分P信息
            parts_dir: 分P输出目录
            llm_api: LLM API服务
            temperature: 温度参数
            max_tokens: 最大token数
            task_id: 任务ID

        Returns:
            dict: 包含分P处理结果的字典
        """
        # 为每个分P创建子目录
        part_dir = parts_dir / f"part_{part_info.part_number}"
        part_dir.mkdir(exist_ok=True)

        timer = Timer()

        # 下载音频
        self._check_cancellation(task_id)
        self.logger.info(f"下载分P {part_info.part_number} 音频：{part_info.url}")
        timer.start()
        audio_file = download_bilibili_audio(
            part_info.url,  # 包含 ?p=N 的URL
            output_format="mp3",
            output_dir=str(part_dir),
        )
        download_time = timer.stop()
        self.logger.info(f"下载完成，耗时 {download_time:.1f} 秒")

        # ASR识别
        self._check_cancellation(task_id)
        self.logger.info(f"ASR识别分P {part_info.part_number}...")
        from src.services.asr import transcribe_audio
        timer.start()
        audio_text = transcribe_audio(audio_file.path, task_id=task_id)
        asr_time = timer.stop()
        self.logger.info(f"ASR识别完成，耗时 {asr_time:.1f} 秒，文本长度 {len(audio_text)}")

        # 保存原始转录
        with open(part_dir / "audio_transcription.txt", "w", encoding="utf-8") as f:
            f.write(audio_text)

        # LLM润色
        self._check_cancellation(task_id)
        self.logger.info(f"LLM润色分P {part_info.part_number}...")
        from src.text_arrangement import polish_text as polish_text_func
        timer.start()
        polished_text, polish_time = polish_text_func(
            audio_text, llm_api, temperature, max_tokens, task_id=task_id
        )
        self.logger.info(f"LLM润色完成，耗时 {polish_time:.1f} 秒")

        # 保存润色文本
        with open(part_dir / "polish_text.txt", "w", encoding="utf-8") as f:
            f.write(polished_text)

        return {
            "part_number": part_info.part_number,
            "title": part_info.title,
            "audio_text": audio_text,
            "polished_text": polished_text,
            "extract_time": download_time + asr_time,
            "polish_time": polish_time,
        }

    def _merge_parts_text(self, part_results: List[dict], output_dir: str) -> str:
        """
        合并各分P的文本，添加章节标题

        Args:
            part_results: 各分P的处理结果列表
            output_dir: 输出目录

        Returns:
            str: 合并后的润色文本
        """
        merged_parts = []

        for result in part_results:
            # 章节分隔符（60个等号）
            chapter_header = (
                f"\n\n{'='*60}\n"
                f"第 {result['part_number']} P: {result['title']}\n"
                f"{'='*60}\n\n"
            )
            merged_parts.append(chapter_header + result["polished_text"])

        merged_text = "\n".join(merged_parts).strip()

        # 保存合并后的文本
        merged_text_path = Path(output_dir) / "merged_polish_text.txt"
        with open(merged_text_path, "w", encoding="utf-8") as f:
            f.write(merged_text)

        self.logger.info(f"合并文本已保存：{merged_text_path}")
        return merged_text

    def _cleanup_task(self, task_id: str):
        """清理任务"""
        if task_id:
            self.task_manager.remove_task(task_id)
