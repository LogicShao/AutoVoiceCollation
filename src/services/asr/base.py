"""
ASR服务基类接口

定义ASR服务的通用接口
"""

from abc import ABC, abstractmethod

from src.utils.logging.logger import get_logger


class BaseASRService(ABC):
    """ASR服务基类"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        # 延迟导入避免循环依赖
        from src.utils.helpers.task_manager import get_task_manager

        self.task_manager = get_task_manager()
        self.model = None

    @abstractmethod
    def load_model(self):
        """
        加载ASR模型

        Raises:
            RuntimeError: 模型加载失败
        """
        pass

    @abstractmethod
    def transcribe(self, audio_path: str, task_id: str | None = None) -> str:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径
            task_id: 任务ID，用于取消控制

        Returns:
            str: 转录文本

        Raises:
            RuntimeError: 转录失败
            TaskCancelledException: 任务被取消
        """
        pass

    def check_cancellation(self, task_id: str | None) -> None:
        """
        检查任务是否被取消

        Args:
            task_id: 任务ID

        Raises:
            TaskCancelledException: 任务已被取消
        """
        if task_id:
            self.task_manager.check_cancellation(task_id)
