import asyncio
import os
from contextlib import suppress
from datetime import datetime, timedelta

import pytest

from src.api.inference_queue import InferenceQueue
from src.core.exceptions import TaskCancelledException


@pytest.fixture
def iq():
    """Create a fresh InferenceQueue with short timeout for testing"""
    InferenceQueue._instance = None
    os.environ["TASK_TIMEOUT"] = "2"
    q = InferenceQueue()
    q._initialized = False
    q.__init__()
    q.task_manager.clear_all()
    yield q
    q.task_manager.clear_all()
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

    def test_expired_pending_task_marked_timeout(self, iq):
        tasks_store = {"test-timeout-pending": {"status": "pending", "message": ""}}
        iq.queue._queue.append(
            {
                "task_id": "test-timeout-pending",
                "task_type": "bilibili",
                "task_data": {},
                "tasks_store": tasks_store,
            }
        )
        iq._task_submitted_at["test-timeout-pending"] = datetime.now() - timedelta(seconds=10)

        marked = iq._mark_expired_pending_tasks()

        assert marked == 1
        assert tasks_store["test-timeout-pending"]["status"] == "timeout"
        assert "test-timeout-pending" not in iq._task_submitted_at

    def test_processing_task_not_marked_timeout_by_pending_monitor(self, iq):
        tasks_store = {"test-processing-timeout": {"status": "processing", "message": ""}}
        iq._task_submitted_at["test-processing-timeout"] = datetime.now() - timedelta(seconds=10)

        marked = iq._mark_expired_pending_tasks()

        assert marked == 0
        assert tasks_store["test-processing-timeout"]["status"] == "processing"
        assert "test-processing-timeout" in iq._task_submitted_at

    def test_terminal_task_not_marked_timeout_by_pending_monitor(self, iq):
        tasks_store = {"test-completed-timeout": {"status": "completed", "message": "done"}}
        iq.queue._queue.append(
            {
                "task_id": "test-completed-timeout",
                "task_type": "bilibili",
                "task_data": {},
                "tasks_store": tasks_store,
            }
        )
        iq._task_submitted_at["test-completed-timeout"] = datetime.now() - timedelta(seconds=10)

        marked = iq._mark_expired_pending_tasks()

        assert marked == 0
        assert tasks_store["test-completed-timeout"]["status"] == "completed"
        assert "test-completed-timeout" in iq._task_submitted_at


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

    def test_cannot_cancel_timeout_task(self, iq):
        tasks_store = {"test-timeout": {"status": "timeout", "message": "等待超时"}}
        result = asyncio.run(iq.cancel_task("test-timeout", tasks_store))
        assert result is False
        assert tasks_store["test-timeout"]["status"] == "timeout"

    def test_processing_cancel_preserves_stop_flag(self, iq):
        iq.task_manager.create_task("test-processing")
        tasks_store = {"test-processing": {"status": "processing", "message": ""}}

        result = asyncio.run(iq.cancel_task("test-processing", tasks_store))

        assert result is True
        assert tasks_store["test-processing"]["status"] == "cancelled"
        assert iq.task_manager.should_stop("test-processing")

    @pytest.mark.asyncio
    async def test_worker_releases_processing_cancel_stop_flag(self, iq, monkeypatch):
        task_id = "test-processing-worker"
        tasks_store = {task_id: {"status": "pending", "message": ""}}
        started = asyncio.Event()
        release = asyncio.Event()

        async def cancellable_process(*args, **kwargs):
            started.set()
            await release.wait()
            raise TaskCancelledException(task_id)

        monkeypatch.setattr(iq, "_process_bilibili_task", cancellable_process)

        queued = await iq.submit_task(
            task_id=task_id,
            task_type="bilibili",
            task_data={"video_url": "https://example.invalid"},
            tasks_store=tasks_store,
        )
        assert queued is True

        worker = asyncio.create_task(iq._worker_loop())
        await asyncio.wait_for(started.wait(), timeout=1)
        assert tasks_store[task_id]["status"] == "processing"

        cancelled = await iq.cancel_task(task_id, tasks_store)
        assert cancelled is True
        assert iq.task_manager.should_stop(task_id)

        release.set()
        await asyncio.wait_for(iq.queue.join(), timeout=1)
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker

        assert tasks_store[task_id]["status"] == "cancelled"
        assert not iq.task_manager.task_exists(task_id)

    @pytest.mark.asyncio
    async def test_worker_skips_timeout_pending_task(self, iq, monkeypatch):
        tasks_store = {"test-timeout-skip": {"status": "pending", "message": ""}}
        called = False

        async def fail_if_called(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("timeout pending task should not be processed")

        monkeypatch.setattr(iq, "_process_bilibili_task", fail_if_called)

        queued = await iq.submit_task(
            task_id="test-timeout-skip",
            task_type="bilibili",
            task_data={"video_url": "https://example.invalid"},
            tasks_store=tasks_store,
        )
        assert queued is True

        marked = iq._mark_expired_pending_tasks(
            now=datetime.now() + timedelta(seconds=iq.task_timeout + 1)
        )
        assert marked == 1

        worker = asyncio.create_task(iq._worker_loop())
        await asyncio.wait_for(iq.queue.join(), timeout=1)
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker

        assert called is False
        assert tasks_store["test-timeout-skip"]["status"] == "timeout"
        assert "test-timeout-skip" not in iq._task_submitted_at

    @pytest.mark.asyncio
    async def test_worker_skips_cancelled_pending_task(self, iq, monkeypatch):
        tasks_store = {"test-pending-skip": {"status": "pending", "message": ""}}
        called = False

        async def fail_if_called(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("cancelled pending task should not be processed")

        monkeypatch.setattr(iq, "_process_bilibili_task", fail_if_called)

        queued = await iq.submit_task(
            task_id="test-pending-skip",
            task_type="bilibili",
            task_data={"video_url": "https://example.invalid"},
            tasks_store=tasks_store,
        )
        assert queued is True

        cancelled = await iq.cancel_task("test-pending-skip", tasks_store)
        assert cancelled is True

        worker = asyncio.create_task(iq._worker_loop())
        await asyncio.wait_for(iq.queue.join(), timeout=1)
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker

        assert called is False
        assert tasks_store["test-pending-skip"]["status"] == "cancelled"
        assert "test-pending-skip" not in iq._task_submitted_at

    @pytest.mark.asyncio
    async def test_worker_releases_stop_flag_for_pending_task(self, iq, monkeypatch):
        task_id = "test-stop-flag-pending"
        tasks_store = {task_id: {"status": "pending", "message": ""}}
        called = False

        async def fail_if_called(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("stopped pending task should not be processed")

        monkeypatch.setattr(iq, "_process_bilibili_task", fail_if_called)

        queued = await iq.submit_task(
            task_id=task_id,
            task_type="bilibili",
            task_data={"video_url": "https://example.invalid"},
            tasks_store=tasks_store,
        )
        assert queued is True

        iq.task_manager.create_task(task_id)
        iq.task_manager.request_cancel(task_id)

        worker = asyncio.create_task(iq._worker_loop())
        await asyncio.wait_for(iq.queue.join(), timeout=1)
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker

        assert called is False
        assert tasks_store[task_id]["status"] == "cancelled"
        assert not iq.task_manager.task_exists(task_id)
        assert task_id not in iq._task_submitted_at

    @pytest.mark.asyncio
    async def test_multipart_error_result_preserves_readable_message(self, iq, monkeypatch):
        task_id = "test-multipart-readable-error"
        message = "所选视频的所有分P均无CC字幕，请尝试其他采样策略"
        tasks_store = {task_id: {"status": "pending", "message": ""}}

        class FakeMultipartProcessor:
            def process(self, *args, **kwargs):
                return {"error": message, "title": "No CC Course"}, 0.0, 0.0, None

        monkeypatch.setattr(iq, "_get_multipart_processor", lambda: FakeMultipartProcessor())

        await iq._process_multipart_task(
            task_id,
            {
                "video_url": "https://example.invalid",
                "selected_parts": [1, 2],
                "llm_api": "http://example.invalid",
                "temperature": 0.1,
                "max_tokens": 1000,
                "part_sample": "cc_only",
            },
            tasks_store,
        )

        assert tasks_store[task_id]["status"] == "failed"
        assert tasks_store[task_id]["message"] == message
        assert tasks_store[task_id]["error"] == message
        assert tasks_store[task_id]["result"]["title"] == "No CC Course"


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
