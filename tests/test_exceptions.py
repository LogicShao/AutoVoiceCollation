"""
异常处理单元测试

测试项目自定义异常类的功能
"""

import pytest

from src.core.exceptions import (
    AutoVoiceCollationError,
    TaskCancelledException,
    TaskNotFoundError,
)


class TestBaseException:
    """测试基础异常类"""

    def test_base_exception_creation(self):
        """测试基础异常创建"""
        exc = AutoVoiceCollationError("测试错误", "TEST_ERROR")
        assert exc.message == "测试错误"
        assert exc.code == "TEST_ERROR"
        assert exc.details == {}
        assert isinstance(exc.timestamp, str)

    def test_base_exception_with_details(self):
        """测试带详情的异常"""
        details = {"key": "value", "number": 123}
        exc = AutoVoiceCollationError("测试错误", "TEST_ERROR", details)
        assert exc.details == details

    def test_to_dict(self):
        """测试转换为字典"""
        exc = AutoVoiceCollationError("测试错误", "TEST_ERROR", {"key": "value"})
        result = exc.to_dict()

        assert result["error"] == "测试错误"
        assert result["code"] == "TEST_ERROR"
        assert result["type"] == "AutoVoiceCollationError"
        assert "timestamp" in result
        assert result["details"] == {"key": "value"}

    def test_str_representation(self):
        """测试字符串表示"""
        exc = AutoVoiceCollationError("测试错误", "TEST_ERROR")
        assert str(exc) == "[TEST_ERROR] 测试错误"

    def test_repr_representation(self):
        """测试repr表示"""
        exc = AutoVoiceCollationError("测试错误", "TEST_ERROR")
        repr_str = repr(exc)
        assert "AutoVoiceCollationError" in repr_str
        assert "测试错误" in repr_str
        assert "TEST_ERROR" in repr_str


class TestTaskExceptions:
    """测试任务异常类"""

    def test_task_cancelled_exception(self):
        """测试任务取消异常"""
        exc = TaskCancelledException("task-123")
        assert exc.code == "TASK_CANCELLED"
        assert exc.details["task_id"] == "task-123"
        assert "task-123" in exc.message

    def test_task_not_found_error(self):
        """测试任务不存在错误"""
        exc = TaskNotFoundError("task-123")
        assert exc.code == "TASK_NOT_FOUND"
        assert exc.details["task_id"] == "task-123"


class TestExceptionRaising:
    """测试异常抛出"""

    def test_raise_and_catch_task_cancelled(self):
        """测试抛出并捕获任务取消异常"""
        with pytest.raises(TaskCancelledException) as exc_info:
            raise TaskCancelledException("task-123")

        assert exc_info.value.code == "TASK_CANCELLED"
        assert "task-123" in str(exc_info.value)


class TestExceptionInheritance:
    """测试异常继承关系"""

    def test_task_error_is_base_exception(self):
        """测试任务错误是基础异常的子类"""
        exc = TaskCancelledException("task-123")
        assert isinstance(exc, AutoVoiceCollationError)
        assert isinstance(exc, Exception)
