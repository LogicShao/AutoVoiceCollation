"""
API 单元测试
使用 FastAPI TestClient 和 pytest 进行单元测试
"""
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api import app, tasks


@pytest.fixture
def client():
    """创建 FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_tasks():
    """每个测试前清空任务状态"""
    tasks.clear()
    yield
    tasks.clear()


class TestRootEndpoints:
    """测试根端点"""

    def test_root_endpoint(self, client):
        """测试根端点返回 API 信息"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AutoVoiceCollation API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "/api/v1/process/bilibili" in data["endpoints"].values()
        assert "/api/v1/summarize" in data["endpoints"].values()

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "config" in data
        assert "asr_model" in data["config"]


class TestBilibiliEndpoint:
    """测试 B站视频处理端点"""

    @patch("api.bilibili_video_download_process")
    def test_process_bilibili_video_success(self, mock_process, client):
        """测试成功处理 B站视频"""
        # 配置 mock
        mock_process.return_value = ("/output/dir", 10.5, 5.2, "/output/result.zip")

        # 发送请求
        payload = {
            "video_url": "https://www.bilibili.com/video/BV1234567890",
            "llm_api": "http://test-llm",
            "temperature": 0.7,
            "max_tokens": 4000,
            "text_only": False,
            "summarize": False
        }
        response = client.post("/api/v1/process/bilibili", json=payload)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        task_id = data["task_id"]
        assert task_id in tasks

    @patch("api.bilibili_video_download_process")
    @patch("api.summarize_text")
    def test_process_bilibili_video_with_summarize(self, mock_summarize, mock_process, client):
        """测试带总结功能的 B站视频处理"""
        # 配置 mock
        mock_process.return_value = (
            {"polished_text": "测试文本", "title": "测试标题"},
            10.5, 5.2, None
        )
        mock_summarize.return_value = "这是总结内容"

        # 发送请求
        payload = {
            "video_url": "https://www.bilibili.com/video/BV1234567890",
            "text_only": True,
            "summarize": True
        }
        response = client.post("/api/v1/process/bilibili", json=payload)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        task_id = data["task_id"]

        # 等待后台任务完成（在测试中同步执行）
        # 注意：这里需要手动触发后台任务
        # 实际测试中可能需要使用 pytest-asyncio


class TestAudioEndpoint:
    """测试音频处理端点"""

    def test_process_audio_invalid_format(self, client):
        """测试上传不支持的文件格式"""
        # 创建一个假的文件
        file_content = b"fake audio content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = client.post(
            "/api/v1/process/audio",
            files=files
        )
        assert response.status_code == 400
        assert "不支持的文件类型" in response.json()["detail"]

    @patch("api.upload_audio")
    def test_process_audio_success(self, mock_upload, client):
        """测试成功处理音频文件"""
        # 配置 mock
        mock_upload.return_value = ("/output/dir", 10.5, 5.2, "/output/result.zip")

        # 创建一个假的音频文件
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", BytesIO(file_content), "audio/mpeg")}

        response = client.post("/api/v1/process/audio", files=files)

        # 验证响应 - 添加详细错误信息
        if response.status_code != 200:
            try:
                error_detail = response.json()
                print(f"\n[ERROR] Status {response.status_code}")
                print(f"Response JSON: {error_detail}")
            except Exception:
                print(f"\n[ERROR] Status {response.status_code}")
                print(f"Response text: {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    @patch("api.upload_audio")
    def test_process_audio_with_summarize(self, mock_upload, client):
        """测试带总结功能的音频处理"""
        # 配置 mock
        mock_upload.return_value = (
            {"polished_text": "测试文本", "title": "测试标题"},
            10.5, 5.2, None
        )

        # 创建一个假的音频文件
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", BytesIO(file_content), "audio/mpeg")}
        data = {
            "text_only": "true",
            "summarize": "true"
        }

        response = client.post("/api/v1/process/audio", files=files, data=data)

        # 验证响应 - 添加详细错误信息
        if response.status_code != 200:
            try:
                error_detail = response.json()
                print(f"\n[ERROR] Status {response.status_code}")
                print(f"Response JSON: {error_detail}")
            except Exception:
                print(f"\n[ERROR] Status {response.status_code}")
                print(f"Response text: {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        result = response.json()
        assert "task_id" in result


class TestBatchEndpoint:
    """测试批量处理端点"""

    def test_process_batch_empty_urls(self, client):
        """测试空 URL 列表"""
        payload = {"urls": []}
        response = client.post("/api/v1/process/batch", json=payload)
        assert response.status_code == 400
        assert "URL列表不能为空" in response.json()["detail"]

    @patch("api.process_multiple_urls")
    def test_process_batch_success(self, mock_process, client):
        """测试成功批量处理"""
        # 配置 mock
        mock_process.return_value = ("结果文本", 20.5, 10.2, None, None, None)

        payload = {
            "urls": [
                "https://www.bilibili.com/video/BV1111111111",
                "https://www.bilibili.com/video/BV2222222222"
            ],
            "text_only": False
        }
        response = client.post("/api/v1/process/batch", json=payload)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "2 个视频" in data["message"]


class TestSubtitleEndpoint:
    """测试字幕处理端点"""

    def test_process_subtitle_invalid_format(self, client):
        """测试上传不支持的视频格式"""
        file_content = b"fake video content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = client.post("/api/v1/process/subtitle", files=files)
        assert response.status_code == 400
        assert "不支持的视频格式" in response.json()["detail"]

    @patch("api.process_subtitles")
    def test_process_subtitle_success(self, mock_process, client):
        """测试成功处理字幕"""
        # 配置 mock
        mock_process.return_value = ("/output/subtitle.srt", "/output/video_with_sub.mp4")

        # 创建一个假的视频文件
        file_content = b"fake video content"
        files = {"file": ("test.mp4", BytesIO(file_content), "video/mp4")}

        response = client.post("/api/v1/process/subtitle", files=files)

        # 验证响应 - 添加详细错误信息
        if response.status_code != 200:
            try:
                error_detail = response.json()
                print(f"\n[ERROR] Status {response.status_code}")
                print(f"Response JSON: {error_detail}")
            except Exception:
                print(f"\n[ERROR] Status {response.status_code}")
                print(f"Response text: {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"


class TestSummarizeEndpoint:
    """测试文本总结端点"""

    @patch("api.summarize_text")
    def test_summarize_success(self, mock_summarize, client):
        """测试成功总结文本"""
        # 配置 mock
        mock_summarize.return_value = "这是总结后的内容"

        payload = {
            "text": "这是一段很长的文本内容，需要进行总结。" * 100,
            "title": "测试标题",
            "llm_api": "http://test-llm",
            "temperature": 0.7,
            "max_tokens": 4000
        }
        response = client.post("/api/v1/summarize", json=payload)

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"] == "这是总结后的内容"
        assert "original_length" in data
        assert "summary_length" in data

    @patch("api.summarize_text", side_effect=Exception("LLM API 错误"))
    def test_summarize_failure(self, mock_summarize, client):
        """测试总结失败的情况"""
        payload = {
            "text": "测试文本",
            "llm_api": "http://test-llm"
        }
        response = client.post("/api/v1/summarize", json=payload)

        # 验证响应
        assert response.status_code == 500
        assert "总结失败" in response.json()["detail"]


class TestTaskStatusEndpoint:
    """测试任务状态查询端点"""

    def test_get_task_status_not_found(self, client):
        """测试查询不存在的任务"""
        response = client.get("/api/v1/task/non-existent-task-id")
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_get_task_status_pending(self, client):
        """测试查询待处理任务"""
        task_id = "test-task-123"
        tasks[task_id] = {"status": "pending", "message": "任务已创建"}

        response = client.get(f"/api/v1/task/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "pending"

    def test_get_task_status_completed(self, client):
        """测试查询已完成任务"""
        task_id = "test-task-456"
        tasks[task_id] = {
            "status": "completed",
            "message": "处理完成",
            "result": {"output_dir": "/output/dir", "extract_time": 10.5}
        }

        response = client.get(f"/api/v1/task/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"]["output_dir"] == "/output/dir"


class TestDownloadEndpoint:
    """测试结果下载端点"""

    def test_download_task_not_found(self, client):
        """测试下载不存在的任务"""
        response = client.get("/api/v1/download/non-existent-task")
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_download_task_not_completed(self, client):
        """测试下载未完成的任务"""
        task_id = "test-task-789"
        tasks[task_id] = {"status": "processing", "message": "正在处理"}

        response = client.get(f"/api/v1/download/{task_id}")
        assert response.status_code == 400
        assert "任务尚未完成" in response.json()["detail"]

    def test_download_file_not_exists(self, client):
        """测试下载不存在的文件"""
        task_id = "test-task-999"
        tasks[task_id] = {
            "status": "completed",
            "result": {"zip_file": "/non/existent/file.zip"}
        }

        response = client.get(f"/api/v1/download/{task_id}")
        assert response.status_code == 404
        assert "结果文件不存在" in response.json()["detail"]

    def test_download_success(self, client, tmp_path):
        """测试成功下载文件"""
        task_id = "test-task-download"
        # 创建一个临时 zip 文件
        zip_file = tmp_path / "result.zip"
        zip_file.write_bytes(b"fake zip content")

        tasks[task_id] = {
            "status": "completed",
            "result": {"zip_file": str(zip_file)}
        }

        response = client.get(f"/api/v1/download/{task_id}")

        # 验证响应
        assert response.status_code == 200
        assert "application/zip" in response.headers["content-type"]


class TestRequestValidation:
    """测试请求验证"""

    def test_bilibili_missing_video_url(self, client):
        """测试缺少视频 URL"""
        payload = {"llm_api": "http://test-llm"}
        response = client.post("/api/v1/process/bilibili", json=payload)
        assert response.status_code == 422  # Validation error

    def test_bilibili_invalid_temperature(self, client):
        """测试无效的温度参数"""
        payload = {
            "video_url": "https://www.bilibili.com/video/BV1234567890",
            "temperature": 3.0  # 超出范围 (0-2)
        }
        response = client.post("/api/v1/process/bilibili", json=payload)
        assert response.status_code == 422

    def test_summarize_missing_text(self, client):
        """测试缺少文本参数"""
        payload = {"llm_api": "http://test-llm"}
        response = client.post("/api/v1/summarize", json=payload)
        assert response.status_code == 422


class TestBackgroundTasks:
    """测试后台任务"""

    @pytest.mark.asyncio
    @patch("api.bilibili_video_download_process")
    async def test_process_bilibili_task_success(self, mock_process):
        """测试 B站视频后台任务成功"""
        from api import process_bilibili_task

        # 配置 mock
        mock_process.return_value = ("/output/dir", 10.5, 5.2, "/output/result.zip")

        task_id = "test-task-bg-1"
        tasks[task_id] = {"status": "pending"}

        # 执行后台任务
        await process_bilibili_task(
            task_id=task_id,
            video_url="https://www.bilibili.com/video/BV1234567890",
            llm_api="http://test-llm",
            temperature=0.7,
            max_tokens=4000,
            text_only=False,
            summarize=False
        )

        # 验证任务状态
        assert tasks[task_id]["status"] == "completed"
        assert "result" in tasks[task_id]
        assert tasks[task_id]["result"]["output_dir"] == "/output/dir"

    @pytest.mark.asyncio
    @patch("api.bilibili_video_download_process", side_effect=Exception("处理错误"))
    async def test_process_bilibili_task_failure(self, mock_process):
        """测试 B站视频后台任务失败"""
        from api import process_bilibili_task

        task_id = "test-task-bg-2"
        tasks[task_id] = {"status": "pending"}

        # 执行后台任务
        await process_bilibili_task(
            task_id=task_id,
            video_url="https://www.bilibili.com/video/BV1234567890",
            llm_api="http://test-llm",
            temperature=0.7,
            max_tokens=4000,
            text_only=False,
            summarize=False
        )

        # 验证任务状态
        assert tasks[task_id]["status"] == "failed"
        assert "处理错误" in tasks[task_id]["message"]

    @pytest.mark.asyncio
    @patch("api.bilibili_video_download_process")
    @patch("api.summarize_text")
    async def test_process_bilibili_task_with_summarize(self, mock_summarize, mock_process):
        """测试带总结功能的后台任务"""
        from api import process_bilibili_task

        # 配置 mock
        mock_process.return_value = (
            {"polished_text": "测试文本", "title": "测试标题"},
            10.5, 5.2, None
        )
        mock_summarize.return_value = "这是总结内容"

        task_id = "test-task-bg-3"
        tasks[task_id] = {"status": "pending"}

        # 执行后台任务
        await process_bilibili_task(
            task_id=task_id,
            video_url="https://www.bilibili.com/video/BV1234567890",
            llm_api="http://test-llm",
            temperature=0.7,
            max_tokens=4000,
            text_only=True,
            summarize=True
        )

        # 验证任务状态和总结结果
        assert tasks[task_id]["status"] == "completed"
        assert "summary" in tasks[task_id]["result"]
        assert tasks[task_id]["result"]["summary"] == "这是总结内容"
        mock_summarize.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
