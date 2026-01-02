"""
异步推理队列

提供单进程、单模型实例的异步推理能力,解决 FastAPI 推理阻塞问题
"""

import asyncio
import os
from pathlib import Path
from asyncio import Queue
from typing import Optional, Dict, Any
from datetime import datetime
import traceback

from src.utils.logging.logger import get_logger
from src.utils.config import get_config
from src.core.processors import AudioProcessor, VideoProcessor, SubtitleProcessor
from src.text_arrangement.summary_by_llm import summarize_text
from src.utils.helpers.task_manager import get_task_manager

logger = get_logger(__name__)


class InferenceQueue:
    """
    异步推理队列（单例模式）

    设计原则：
    - 全局唯一实例，处理器持有唯一模型
    - 串行处理任务（避免 GPU 冲突）
    - 异步接口，不阻塞 FastAPI 事件循环
    """

    _instance: Optional["InferenceQueue"] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化队列（仅执行一次）"""
        if self._initialized:
            return

        self.queue: Queue = Queue(maxsize=50)  # 限制队列容量,避免积压
        self.worker_task: Optional[asyncio.Task] = None
        self._initialized = True

        # 初始化处理器（延迟加载模型）
        self.audio_processor = AudioProcessor()
        self.video_processor = VideoProcessor()
        self.subtitle_processor = SubtitleProcessor()
        self.task_manager = get_task_manager()

        logger.info("推理队列初始化完成")

    async def start(self):
        """启动工作循环"""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker_loop())
            logger.info("✅ 推理工作线程已启动")

    async def stop(self):
        """停止工作循环"""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                logger.info("推理工作线程已停止")

    async def submit_task(
        self,
        task_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        tasks_store: Dict,
    ):
        """
        提交任务到队列

        Args:
            task_id: 任务 ID
            task_type: 任务类型（bilibili, audio, batch, subtitle）
            task_data: 任务数据
            tasks_store: 任务状态存储（引用传递）
        """
        try:
            await self.queue.put(
                {
                    "task_id": task_id,
                    "task_type": task_type,
                    "task_data": task_data,
                    "tasks_store": tasks_store,
                }
            )
            logger.info(f"任务已提交到队列: {task_id}, 队列长度: {self.queue.qsize()}")
        except asyncio.QueueFull:
            logger.error(f"队列已满,任务提交失败: {task_id}")
            tasks_store[task_id].update(
                {
                    "status": "failed",
                    "message": "队列已满,请稍后重试",
                    "error": "Queue is full",
                    "completed_at": datetime.now().isoformat(),
                }
            )

    def _is_task_cancelled(self, task_id: str, tasks_store: Dict) -> bool:
        task_info = tasks_store.get(task_id, {})
        return task_info.get("status") == "cancelled" or self.task_manager.should_stop(
            task_id
        )

    def _mark_task_cancelled(
        self, task_id: str, tasks_store: Dict, message: str = "任务已取消"
    ) -> None:
        task_info = tasks_store.get(task_id)
        if task_info is None:
            tasks_store[task_id] = {}
            task_info = tasks_store[task_id]

        task_info.update(
            {
                "status": "cancelled",
                "message": message,
                "completed_at": datetime.now().isoformat(),
            }
        )
        self.task_manager.remove_task(task_id)

    def _extract_output_dir(self, output_data: Any) -> str:
        if isinstance(output_data, dict):
            return output_data.get("output_dir", "")
        return output_data or ""

    def _build_lazy_zip_path(self, task_id: str, output_dir: str) -> str:
        if not output_dir:
            return ""
        config = get_config()
        safe_name = Path(output_dir).name or "output"
        return str(config.paths.temp_dir / f"{safe_name}_{task_id}.zip")

    async def _worker_loop(self):
        """工作循环：持续从队列取任务并执行"""
        logger.info("工作循环已启动，等待任务...")

        while True:
            try:
                task_item = await self.queue.get()

                task_id = task_item["task_id"]
                task_type = task_item["task_type"]
                task_data = task_item["task_data"]
                tasks_store = task_item["tasks_store"]

                logger.info(
                    f"开始处理任务: {task_id}, 类型: {task_type}, 队列剩余: {self.queue.qsize()}"
                )

                try:
                    if self._is_task_cancelled(task_id, tasks_store):
                        self._mark_task_cancelled(task_id, tasks_store)
                        continue

                    # 更新状态为处理中
                    tasks_store[task_id]["status"] = "processing"

                    # 根据类型调用处理函数
                    if task_type == "bilibili":
                        await self._process_bilibili_task(
                            task_id, task_data, tasks_store
                        )
                    elif task_type == "audio":
                        await self._process_audio_task(task_id, task_data, tasks_store)
                    elif task_type == "batch":
                        await self._process_batch_task(task_id, task_data, tasks_store)
                    elif task_type == "subtitle":
                        await self._process_subtitle_task(
                            task_id, task_data, tasks_store
                        )
                    else:
                        raise ValueError(f"未知的任务类型: {task_type}")

                    if tasks_store.get(task_id, {}).get("status") == "cancelled":
                        logger.info(f"任务已取消: {task_id}")
                    else:
                        logger.info(f"✅ 任务完成: {task_id}")

                except Exception as e:
                    logger.error(f"任务失败: {task_id}, 错误: {e}", exc_info=True)
                    tasks_store[task_id].update(
                        {
                            "status": "failed",
                            "message": f"处理失败: {str(e)}",
                            "error": traceback.format_exc(),
                            "completed_at": datetime.now().isoformat(),
                        }
                    )

                finally:
                    self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("工作循环被取消")
                break
            except Exception as e:
                logger.error(f"工作循环异常: {e}", exc_info=True)

    async def _process_bilibili_task(self, task_id: str, data: Dict, tasks_store: Dict):
        """处理 B站视频任务"""
        loop = asyncio.get_event_loop()

        # 创建任务（如果不存在）
        if not self.task_manager.task_exists(task_id):
            self.task_manager.create_task(task_id)

        # 在线程池中执行同步处理函数
        output_data, extract_time, polish_time, zip_file = await loop.run_in_executor(
            None,
            self.video_processor.process,
            data["video_url"],
            data["llm_api"],
            data["temperature"],
            data["max_tokens"],
            data["text_only"],
            task_id,  # 传递 task_id 以支持取消
        )

        completed_at = datetime.now().isoformat()

        if self._is_task_cancelled(task_id, tasks_store):
            self._mark_task_cancelled(task_id, tasks_store)
            return

        if data["text_only"]:
            result_data = output_data

            # 如果需要总结,对润色后的文本进行总结
            if (
                data.get("summarize")
                and isinstance(result_data, dict)
                and "polished_text" in result_data
            ):
                if self._is_task_cancelled(task_id, tasks_store):
                    self._mark_task_cancelled(task_id, tasks_store)
                    return
                tasks_store[task_id]["message"] = "正在生成总结"
                summary = await loop.run_in_executor(
                    None,
                    summarize_text,
                    result_data["polished_text"],
                    data["llm_api"],
                    data["temperature"],
                    data["max_tokens"],
                    result_data.get("title", ""),
                )
                result_data["summary"] = summary
                completed_at = datetime.now().isoformat()

            output_dir = self._extract_output_dir(result_data)
            if output_dir and not result_data.get("zip_file"):
                result_data["zip_file"] = self._build_lazy_zip_path(
                    task_id, output_dir
                )

            if self._is_task_cancelled(task_id, tasks_store):
                self._mark_task_cancelled(task_id, tasks_store)
                return

            tasks_store[task_id].update(
                {
                    "status": "completed",
                    "message": "处理完成",
                    "result": result_data,
                    "completed_at": completed_at,
                }
            )
        else:
            if self._is_task_cancelled(task_id, tasks_store):
                self._mark_task_cancelled(task_id, tasks_store)
                return

            output_dir = self._extract_output_dir(output_data)
            zip_file_path = zip_file or self._build_lazy_zip_path(task_id, output_dir)
            tasks_store[task_id].update(
                {
                    "status": "completed",
                    "message": "处理完成",
                    "result": {
                        "output_dir": output_dir,
                        "extract_time": extract_time,
                        "polish_time": polish_time,
                        "zip_file": zip_file_path,
                    },
                    "completed_at": completed_at,
                }
            )

    async def _process_audio_task(self, task_id: str, data: Dict, tasks_store: Dict):
        """处理音频任务"""
        loop = asyncio.get_event_loop()

        # 创建任务（如果不存在）
        if not self.task_manager.task_exists(task_id):
            self.task_manager.create_task(task_id)

        # 在线程池中执行同步处理函数
        output_data, extract_time, polish_time, zip_file = await loop.run_in_executor(
            None,
            self.audio_processor.process_uploaded_audio,
            data["audio_path"],
            data["llm_api"],
            data["temperature"],
            data["max_tokens"],
            data["text_only"],
            task_id,  # 传递 task_id 以支持取消
        )

        # 清理临时文件
        if os.path.exists(data["audio_path"]):
            await loop.run_in_executor(None, os.remove, data["audio_path"])

        completed_at = datetime.now().isoformat()

        if self._is_task_cancelled(task_id, tasks_store):
            self._mark_task_cancelled(task_id, tasks_store)
            return

        if data["text_only"]:
            result_data = output_data

            # 如果需要总结,对润色后的文本进行总结
            if (
                data.get("summarize")
                and isinstance(result_data, dict)
                and "polished_text" in result_data
            ):
                if self._is_task_cancelled(task_id, tasks_store):
                    self._mark_task_cancelled(task_id, tasks_store)
                    return
                tasks_store[task_id]["message"] = "正在生成总结"
                summary = await loop.run_in_executor(
                    None,
                    summarize_text,
                    result_data["polished_text"],
                    data["llm_api"],
                    data["temperature"],
                    data["max_tokens"],
                    result_data.get("title", ""),
                )
                result_data["summary"] = summary
                completed_at = datetime.now().isoformat()

            output_dir = self._extract_output_dir(result_data)
            if output_dir and not result_data.get("zip_file"):
                result_data["zip_file"] = self._build_lazy_zip_path(
                    task_id, output_dir
                )

            if self._is_task_cancelled(task_id, tasks_store):
                self._mark_task_cancelled(task_id, tasks_store)
                return

            tasks_store[task_id].update(
                {
                    "status": "completed",
                    "message": "处理完成",
                    "result": result_data,
                    "completed_at": completed_at,
                }
            )
        else:
            if self._is_task_cancelled(task_id, tasks_store):
                self._mark_task_cancelled(task_id, tasks_store)
                return

            output_dir = self._extract_output_dir(output_data)
            zip_file_path = zip_file or self._build_lazy_zip_path(task_id, output_dir)
            tasks_store[task_id].update(
                {
                    "status": "completed",
                    "message": "处理完成",
                    "result": {
                        "output_dir": output_dir,
                        "extract_time": extract_time,
                        "polish_time": polish_time,
                        "zip_file": zip_file_path,
                    },
                    "completed_at": completed_at,
                }
            )

    async def _process_batch_task(self, task_id: str, data: Dict, tasks_store: Dict):
        """处理批量任务"""
        loop = asyncio.get_event_loop()

        # 创建任务（如果不存在）
        if not self.task_manager.task_exists(task_id):
            self.task_manager.create_task(task_id)

        # 将URL字符串转为列表
        if isinstance(data.get("urls"), str):
            urls = data["urls"]
        else:
            urls = "\n".join(data.get("urls", []))

        # 在线程池中执行同步处理函数
        status_message, total_time, _, _, _, _ = await loop.run_in_executor(
            None,
            self.video_processor.process_batch,
            urls,
            data["llm_api"],
            data["temperature"],
            data["max_tokens"],
            data["text_only"],
            task_id,  # 传递 task_id 以支持取消
        )

        if self._is_task_cancelled(task_id, tasks_store):
            self._mark_task_cancelled(task_id, tasks_store)
            return

        tasks_store[task_id].update(
            {
                "status": "completed",
                "message": "批量处理完成",
                "result": {
                    "status_message": status_message,
                    "total_time": total_time,
                },
                "completed_at": datetime.now().isoformat(),
            }
        )

    async def _process_subtitle_task(self, task_id: str, data: Dict, tasks_store: Dict):
        """处理字幕任务"""
        loop = asyncio.get_event_loop()

        # 创建任务（如果不存在）
        if not self.task_manager.task_exists(task_id):
            self.task_manager.create_task(task_id)

        # 在线程池中执行同步处理函数
        subtitle_path, video_path, info = await loop.run_in_executor(
            None,
            self.subtitle_processor.process,
            data["video_path"],
            # 传递其他字幕配置参数...
        )

        if self._is_task_cancelled(task_id, tasks_store):
            self._mark_task_cancelled(task_id, tasks_store)
            return

        tasks_store[task_id].update(
            {
                "status": "completed",
                "message": "字幕生成完成",
                "result": {
                    "subtitle_file": subtitle_path,
                    "output_video": video_path,
                    "info": info,
                },
                "completed_at": datetime.now().isoformat(),
            }
        )


# 全局单例
_inference_queue: Optional[InferenceQueue] = None


def get_inference_queue() -> InferenceQueue:
    """获取全局推理队列实例"""
    global _inference_queue
    if _inference_queue is None:
        _inference_queue = InferenceQueue()
    return _inference_queue
