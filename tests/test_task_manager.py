"""
任务管理器单元测试
测试任务的创建、停止、状态查询和取消异常处理
"""
import threading
import time

import pytest

from src.core.exceptions import TaskCancelledException
from src.task_manager import TaskManager, get_task_manager


class TestTaskManager:
    """测试任务管理器核心功能"""

    @pytest.fixture
    def task_manager(self):
        """每个测试前清空任务管理器"""
        tm = get_task_manager()
        tm.clear_all()
        yield tm
        tm.clear_all()

    def test_singleton_pattern(self):
        """测试单例模式 - 确保只有一个实例"""
        tm1 = TaskManager()
        tm2 = TaskManager()
        tm3 = get_task_manager()
        assert tm1 is tm2
        assert tm2 is tm3

    def test_create_task(self, task_manager):
        """测试创建任务"""
        task_id = "test-task-001"
        task_manager.create_task(task_id)

        assert task_manager.task_exists(task_id)
        assert not task_manager.should_stop(task_id)

    def test_task_not_exists(self, task_manager):
        """测试查询不存在的任务"""
        assert not task_manager.task_exists("non-existent-task")
        assert not task_manager.should_stop("non-existent-task")

    def test_stop_task(self, task_manager):
        """测试停止任务"""
        task_id = "test-task-002"
        task_manager.create_task(task_id)

        assert not task_manager.should_stop(task_id)

        task_manager.stop_task(task_id)
        assert task_manager.should_stop(task_id)

    def test_stop_nonexistent_task(self, task_manager):
        """测试停止不存在的任务 - 应该不抛出异常"""
        task_manager.stop_task("non-existent-task")
        # 不应该抛出异常，只会记录警告

    def test_check_cancellation_not_cancelled(self, task_manager):
        """测试未取消任务的取消检查 - 不应抛出异常"""
        task_id = "test-task-003"
        task_manager.create_task(task_id)

        # 不应该抛出异常
        task_manager.check_cancellation(task_id)

    def test_check_cancellation_cancelled(self, task_manager):
        """测试已取消任务的取消检查 - 应抛出 TaskCancelledException"""
        task_id = "test-task-004"
        task_manager.create_task(task_id)
        task_manager.stop_task(task_id)

        with pytest.raises(TaskCancelledException) as exc_info:
            task_manager.check_cancellation(task_id)

        assert task_id in str(exc_info.value)

    def test_remove_task(self, task_manager):
        """测试移除任务"""
        task_id = "test-task-005"
        task_manager.create_task(task_id)
        assert task_manager.task_exists(task_id)

        task_manager.remove_task(task_id)
        assert not task_manager.task_exists(task_id)

    def test_remove_nonexistent_task(self, task_manager):
        """测试移除不存在的任务 - 应该不抛出异常"""
        task_manager.remove_task("non-existent-task")
        # 不应该抛出异常

    def test_clear_all_tasks(self, task_manager):
        """测试清除所有任务"""
        task_manager.create_task("task-1")
        task_manager.create_task("task-2")
        task_manager.create_task("task-3")

        assert task_manager.task_exists("task-1")
        assert task_manager.task_exists("task-2")
        assert task_manager.task_exists("task-3")

        task_manager.clear_all()

        assert not task_manager.task_exists("task-1")
        assert not task_manager.task_exists("task-2")
        assert not task_manager.task_exists("task-3")

    def test_concurrent_task_creation(self, task_manager):
        """测试并发创建任务 - 确保线程安全"""
        num_threads = 10
        tasks_per_thread = 5
        created_tasks = []
        lock = threading.Lock()

        def create_tasks(thread_id):
            for i in range(tasks_per_thread):
                task_id = f"thread-{thread_id}-task-{i}"
                task_manager.create_task(task_id)
                with lock:
                    created_tasks.append(task_id)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=create_tasks, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证所有任务都已创建
        for task_id in created_tasks:
            assert task_manager.task_exists(task_id)

    def test_concurrent_stop_and_check(self, task_manager):
        """测试并发停止和检查任务 - 确保线程安全"""
        task_id = "concurrent-test-task"
        task_manager.create_task(task_id)

        stop_completed = False
        check_raised_exception = False

        def stop_task():
            nonlocal stop_completed
            time.sleep(0.01)  # 稍微延迟以增加竞争条件
            task_manager.stop_task(task_id)
            stop_completed = True

        def check_task():
            nonlocal check_raised_exception
            time.sleep(0.02)  # 延迟更长，确保 stop 先执行
            try:
                task_manager.check_cancellation(task_id)
            except TaskCancelledException:
                check_raised_exception = True

        t1 = threading.Thread(target=stop_task)
        t2 = threading.Thread(target=check_task)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        assert stop_completed
        assert check_raised_exception

    def test_task_lifecycle(self, task_manager):
        """测试完整任务生命周期"""
        task_id = "lifecycle-task"

        # 1. 创建
        task_manager.create_task(task_id)
        assert task_manager.task_exists(task_id)
        assert not task_manager.should_stop(task_id)

        # 2. 执行中（模拟检查点）
        task_manager.check_cancellation(task_id)  # 不应抛出异常

        # 3. 请求停止
        task_manager.stop_task(task_id)
        assert task_manager.should_stop(task_id)

        # 4. 检查取消
        with pytest.raises(TaskCancelledException):
            task_manager.check_cancellation(task_id)

        # 5. 清理
        task_manager.remove_task(task_id)
        assert not task_manager.task_exists(task_id)


class TestTaskCancelledException:
    """测试任务取消异常"""

    def test_exception_creation(self):
        """测试异常创建"""
        msg = "Task test-123 has been cancelled"
        exc = TaskCancelledException(msg)
        assert str(exc) == msg

    def test_exception_inheritance(self):
        """测试异常继承 - 应该是 Exception 的子类"""
        exc = TaskCancelledException("test")
        assert isinstance(exc, Exception)

    def test_exception_can_be_caught(self):
        """测试异常可以被捕获"""

        def task_that_raises():
            raise TaskCancelledException("Task cancelled")

        with pytest.raises(TaskCancelledException) as exc_info:
            task_that_raises()

        assert "cancelled" in str(exc_info.value)

    def test_exception_in_try_except(self):
        """测试在 try-except 块中捕获异常"""
        caught = False

        try:
            raise TaskCancelledException("Test cancellation")
        except TaskCancelledException:
            caught = True

        assert caught


class TestTaskManagerEdgeCases:
    """测试边界情况和异常场景"""

    @pytest.fixture
    def task_manager(self):
        """每个测试前清空任务管理器"""
        tm = get_task_manager()
        tm.clear_all()
        yield tm
        tm.clear_all()

    def test_duplicate_task_creation(self, task_manager):
        """测试重复创建同一任务"""
        task_id = "duplicate-task"
        task_manager.create_task(task_id)
        task_manager.create_task(task_id)  # 重复创建

        # 任务状态应该被重置为未停止
        assert not task_manager.should_stop(task_id)

    def test_stop_then_recreate(self, task_manager):
        """测试停止后重新创建任务"""
        task_id = "stop-recreate-task"

        # 创建并停止
        task_manager.create_task(task_id)
        task_manager.stop_task(task_id)
        assert task_manager.should_stop(task_id)

        # 重新创建
        task_manager.create_task(task_id)
        # 状态应该被重置
        assert not task_manager.should_stop(task_id)

    def test_multiple_stops(self, task_manager):
        """测试多次停止同一任务"""
        task_id = "multiple-stop-task"
        task_manager.create_task(task_id)

        task_manager.stop_task(task_id)
        task_manager.stop_task(task_id)
        task_manager.stop_task(task_id)

        assert task_manager.should_stop(task_id)

    def test_empty_task_id(self, task_manager):
        """测试空任务 ID"""
        task_manager.create_task("")
        assert task_manager.task_exists("")

        task_manager.stop_task("")
        assert task_manager.should_stop("")

    def test_unicode_task_id(self, task_manager):
        """测试 Unicode 任务 ID"""
        task_id = "任务-测试-123-🎯"
        task_manager.create_task(task_id)
        assert task_manager.task_exists(task_id)

        task_manager.stop_task(task_id)
        assert task_manager.should_stop(task_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
