"""
异步推理队列测试
"""

import asyncio
from contextlib import suppress
from datetime import datetime

import pytest

from src.api.inference_queue import get_inference_queue
from src.core.exceptions import TaskCancelledException


async def _wait_for_status(tasks_store: dict, task_id: str, expected_status: str) -> None:
    for _ in range(50):
        if tasks_store[task_id]["status"] == expected_status:
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"任务状态未变为 {expected_status}: {tasks_store[task_id]}")


@pytest.fixture
def inference_queue():
    queue = get_inference_queue()
    queue.task_manager.clear_all()
    queue.queue = asyncio.Queue(maxsize=50)
    queue.worker_task = None
    return queue


class TestInferenceQueue:
    @pytest.mark.asyncio
    async def test_submit_task_returns_false_when_queue_is_full(self, inference_queue):
        """测试队列满载时立即失败"""
        inference_queue.queue = asyncio.Queue(maxsize=1)
        inference_queue.queue.put_nowait(
            {
                "task_id": "occupied",
                "task_type": "audio",
                "task_data": {},
                "tasks_store": {},
            }
        )

        task_id = "task-queue-full"
        tasks_store = {
            task_id: {
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
        }

        queued = await inference_queue.submit_task(task_id, "audio", {}, tasks_store)

        assert queued is False
        assert tasks_store[task_id]["status"] == "failed"
        assert tasks_store[task_id]["error"] == "Queue is full"

    @pytest.mark.asyncio
    async def test_worker_marks_task_cancelled_when_processor_raises(
        self, monkeypatch, inference_queue
    ):
        """测试处理器取消时队列会标记任务已取消"""
        task_id = "task-cancelled"
        tasks_store = {
            task_id: {
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
        }

        async def raise_cancel(*args, **kwargs):
            raise TaskCancelledException(task_id)

        monkeypatch.setattr(inference_queue, "_process_audio_task", raise_cancel)

        worker = asyncio.create_task(inference_queue._worker_loop())
        try:
            inference_queue.queue.put_nowait(
                {
                    "task_id": task_id,
                    "task_type": "audio",
                    "task_data": {},
                    "tasks_store": tasks_store,
                }
            )
            await _wait_for_status(tasks_store, task_id, "cancelled")
            assert "任务" in tasks_store[task_id]["message"]
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker

    @pytest.mark.asyncio
    async def test_worker_marks_task_failed_when_processor_raises_error(
        self, monkeypatch, inference_queue
    ):
        """测试处理器异常时队列会标记任务失败"""
        task_id = "task-failed"
        tasks_store = {
            task_id: {
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
        }

        async def raise_error(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(inference_queue, "_process_audio_task", raise_error)

        worker = asyncio.create_task(inference_queue._worker_loop())
        try:
            inference_queue.queue.put_nowait(
                {
                    "task_id": task_id,
                    "task_type": "audio",
                    "task_data": {},
                    "tasks_store": tasks_store,
                }
            )
            await _wait_for_status(tasks_store, task_id, "failed")
            assert "boom" in tasks_store[task_id]["message"]
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker
