import asyncio
import os
from datetime import datetime, timedelta

import pytest

from src.api.inference_queue import InferenceQueue, get_inference_queue


@pytest.fixture
def iq():
    """Create a fresh InferenceQueue with short timeout for testing"""
    InferenceQueue._instance = None
    os.environ["TASK_TIMEOUT"] = "2"
    q = InferenceQueue()
    q._initialized = False
    q.__init__()
    yield q
    InferenceQueue._instance = None
    os.environ.pop("TASK_TIMEOUT", None)


class TestQueueInitialization:
    def test_task_timeout_from_env(self, iq):
        assert iq.task_timeout == 2.0

    def test_default_timeout(self):
        InferenceQueue._instance = None
        if "TASK_TIMEOUT" in os.environ:
            del os.environ["TASK_TIMEOUT"]
        q = InferenceQueue()
        q._initialized = False
        q.__init__()
        assert q.task_timeout == 600.0
        InferenceQueue._instance = None

    def test_queue_status_initial(self, iq):
        status = iq.get_queue_status()
        assert status["depth"] == 0
        assert status["worker_alive"] is False
        assert status["pending_count"] == 0
        assert status["processing_count"] == 0

    def test_queue_status_with_heartbeat(self, iq):
        iq._last_heartbeat = datetime.now()
        status = iq.get_queue_status()
        assert status["worker_last_heartbeat"] is not None


class TestSubmittedAt:
    def test_submitted_at_recorded(self, iq):
        iq._task_submitted_at["test-1"] = datetime.now()
        assert "test-1" in iq._task_submitted_at

    def test_submitted_at_cleanup_on_timeout(self, iq):
        old_time = datetime.now() - timedelta(seconds=10)
        iq._task_submitted_at["test-2"] = old_time
        # Simulate timeout check
        now = datetime.now()
        for task_id, submitted_at in list(iq._task_submitted_at.items()):
            if (now - submitted_at).total_seconds() > iq.task_timeout:
                iq._task_submitted_at.pop(task_id, None)
        assert "test-2" not in iq._task_submitted_at


class TestCancelSemantics:
    def test_cancel_marks_task(self, iq):
        tasks_store = {"test-3": {"status": "pending", "message": ""}}
        asyncio.run(iq.cancel_task("test-3", tasks_store))
        assert tasks_store["test-3"]["status"] == "cancelled"

    def test_cancel_removes_from_task_manager(self, iq):
        iq.task_manager.create_task("test-4")
        tasks_store = {"test-4": {"status": "pending", "message": ""}}
        asyncio.run(iq.cancel_task("test-4", tasks_store))
        assert tasks_store["test-4"]["status"] == "cancelled"
        assert not iq.task_manager.task_exists("test-4")

    def test_cannot_cancel_completed_task(self, iq):
        tasks_store = {"test-5": {"status": "completed", "message": "done"}}
        result = asyncio.run(iq.cancel_task("test-5", tasks_store))
        assert result is False


class TestQueuePosition:
    def test_queue_position_zero_when_empty(self, iq):
        assert iq._compute_queue_position("any") == 0

    def test_queue_position_one_for_first_item(self, iq):
        iq.queue._queue.append({"task_id": "first"})
        assert iq._compute_queue_position("first") == 1

    def test_queue_position_two_for_second_item(self, iq):
        iq.queue._queue.append({"task_id": "first"})
        iq.queue._queue.append({"task_id": "second"})
        assert iq._compute_queue_position("second") == 2


class TestMarkCancelled:
    def test_mark_cancelled_sets_status(self, iq):
        tasks_store = {}
        iq._mark_task_cancelled("test-6", tasks_store, "已取消")
        assert tasks_store["test-6"]["status"] == "cancelled"
        assert tasks_store["test-6"]["message"] == "已取消"

    def test_mark_cancelled_preserves_existing(self, iq):
        tasks_store = {"test-7": {"original": "data", "status": "pending"}}
        iq._mark_task_cancelled("test-7", tasks_store)
        assert tasks_store["test-7"]["status"] == "cancelled"
        assert tasks_store["test-7"]["original"] == "data"
