"""
基础处理器接口

定义所有处理器的通用接口和基础功能
"""

import uuid
from abc import ABC, abstractmethod

from src.utils.logging.logger import get_logger


class BaseProcessor(ABC):
    """处理器基类"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        # 延迟导入避免循环依赖
        from src.utils.helpers.task_manager import get_task_manager

        self.task_manager = get_task_manager()

    def _ensure_task(self, task_id: str | None = None) -> str:
        """
        确保任务存在，如果不存在则创建

        Args:
            task_id: 可选的任务ID

        Returns:
            str: 任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        if not self.task_manager.task_exists(task_id):
            self.task_manager.create_task(task_id)

        return task_id

    def _check_cancellation(self, task_id: str) -> None:
        """
        检查任务是否被取消

        Args:
            task_id: 任务ID

        Raises:
            TaskCancelledException: 任务已被取消
        """
        self.task_manager.check_cancellation(task_id)

    def _cleanup_task(self, task_id: str) -> None:
        """
        清理任务

        Args:
            task_id: 任务ID
        """
        if task_id:
            self.task_manager.remove_task(task_id)

    @abstractmethod
    def process(self, *args, **kwargs):
        """
        处理方法，子类必须实现
        """
        pass
