"""
任务管理模块
用于控制任务的终止和状态
"""

import threading
from typing import Dict

from src.utils.logging.logger import get_logger
from src.core.exceptions import TaskCancelledException

logger = get_logger(__name__)


class TaskManager:
    """任务管理器，使用单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._stop_flags: Dict[str, bool] = {}
        self._flags_lock = threading.Lock()

    def create_task(self, task_id: str) -> None:
        """创建一个新任务"""
        with self._flags_lock:
            self._stop_flags[task_id] = False
            logger.debug(f"Task created: {task_id}")

    def task_exists(self, task_id: str) -> bool:
        """检查任务是否存在"""
        with self._flags_lock:
            return task_id in self._stop_flags

    def stop_task(self, task_id: str) -> None:
        """请求停止指定任务"""
        with self._flags_lock:
            if task_id in self._stop_flags:
                self._stop_flags[task_id] = True
                logger.info(f"Task stop requested: {task_id}")
            else:
                logger.warning(f"Task not found: {task_id}")

    def should_stop(self, task_id: str) -> bool:
        """检查任务是否应该停止"""
        with self._flags_lock:
            return self._stop_flags.get(task_id, False)

    def check_cancellation(self, task_id: str) -> None:
        """
        检查任务是否被取消，如果被取消则抛出异常

        Args:
            task_id: 任务ID

        Raises:
            TaskCancelledException: 任务已被取消
        """
        if self.should_stop(task_id):
            logger.warning(f"Task cancellation detected: {task_id}")
            raise TaskCancelledException(task_id)

    def remove_task(self, task_id: str) -> None:
        """移除任务"""
        with self._flags_lock:
            if task_id in self._stop_flags:
                del self._stop_flags[task_id]
                logger.debug(f"Task removed: {task_id}")

    def clear_all(self) -> None:
        """清除所有任务"""
        with self._flags_lock:
            self._stop_flags.clear()
            logger.info("All tasks cleared")


# 全局任务管理器实例
_task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    return _task_manager
