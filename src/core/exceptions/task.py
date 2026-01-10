"""
任务管理相关异常类

定义任务生命周期和管理相关的异常
"""

from .base import AutoVoiceCollationError


class TaskError(AutoVoiceCollationError):
    """任务基础异常"""

    def __init__(self, message: str, task_id: str | None = None):
        details = {"task_id": task_id} if task_id else {}
        super().__init__(message, "TASK_ERROR", details)


class TaskCancelledException(TaskError):
    """任务取消异常

    当任务被用户主动取消时抛出此异常
    """

    def __init__(self, task_id: str):
        super().__init__(f"任务 {task_id} 已取消", task_id)
        self.code = "TASK_CANCELLED"


class TaskNotFoundError(TaskError):
    """任务不存在异常"""

    def __init__(self, task_id: str):
        super().__init__(f"任务 {task_id} 不存在", task_id)
        self.code = "TASK_NOT_FOUND"


class TaskAlreadyExistsError(TaskError):
    """任务已存在异常"""

    def __init__(self, task_id: str):
        super().__init__(f"任务 {task_id} 已存在", task_id)
        self.code = "TASK_ALREADY_EXISTS"


class TaskTimeoutError(TaskError):
    """任务超时异常"""

    def __init__(self, task_id: str, timeout: float | None = None):
        super().__init__(f"任务 {task_id} 执行超时", task_id)
        self.code = "TASK_TIMEOUT"
        if timeout:
            self.details["timeout"] = timeout


class TaskStatusError(TaskError):
    """任务状态错误异常

    当尝试对处于不合法状态的任务执行操作时抛出
    """

    def __init__(self, message: str, task_id: str, current_status: str):
        super().__init__(message, task_id)
        self.code = "TASK_STATUS_ERROR"
        self.details["current_status"] = current_status
