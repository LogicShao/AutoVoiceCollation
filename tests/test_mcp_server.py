import asyncio
import inspect
import json
from unittest.mock import patch


class TestMcpServerImports:
    def test_module_imports(self):
        from src.mcp.server import main, mcp

        assert mcp is not None
        assert callable(main)

    def test_tools_registered(self):
        from src.mcp.server import mcp

        tool_names = [t.name for t in mcp._tool_manager._tools.values()]
        assert "process_bilibili" in tool_names
        assert "process_audio" in tool_names
        assert "process_batch" in tool_names
        assert "get_task_status" in tool_names
        assert "cancel_task" in tool_names


class TestProcessBilibili:
    def test_signature_has_no_part_sample(self):
        from src.mcp.server import process_bilibili

        assert "part_sample" not in inspect.signature(process_bilibili).parameters

    def test_empty_url_returns_error(self):
        from src.mcp.server import process_bilibili

        result = asyncio.run(process_bilibili(url=""))
        assert "error" in result

    def test_whitespace_url_returns_error(self):
        from src.mcp.server import process_bilibili

        result = asyncio.run(process_bilibili(url="   "))
        assert "error" in result


class TestProcessAudio:
    def test_empty_path_returns_error(self):
        from src.mcp.server import process_audio

        result = asyncio.run(process_audio(file_path=""))
        assert "error" in result

    def test_nonexistent_file_returns_error(self):
        from src.mcp.server import process_audio

        result = asyncio.run(process_audio(file_path="/nonexistent/file.mp3"))
        assert "error" in result

    def test_unsupported_extension_returns_error(self):
        from src.mcp.server import process_audio

        result = asyncio.run(process_audio(file_path="/tmp/test.txt"))
        assert "error" in result


class TestProcessBatch:
    def test_signature_has_no_part_sample(self):
        from src.mcp.server import process_batch

        assert "part_sample" not in inspect.signature(process_batch).parameters

    def test_empty_list_returns_error(self):
        from src.mcp.server import process_batch

        result = asyncio.run(process_batch(urls=[]))
        assert "error" in result

    def test_whitespace_only_urls_returns_error(self):
        from src.mcp.server import process_batch

        result = asyncio.run(process_batch(urls=["   ", ""]))
        assert "error" in result


class TestGetTaskStatus:
    def test_unknown_task_returns_error(self):
        from src.mcp.server import get_task_status

        result = asyncio.run(get_task_status(task_id="nonexistent"))
        assert "error" in result


class TestCancelTask:
    def test_unknown_task_returns_error(self):
        from src.mcp.server import cancel_task

        result = asyncio.run(cancel_task(task_id="nonexistent"))
        assert "error" in result


class TestAnalysisPayload:
    def test_get_task_status_includes_metadata_in_analysis(self):
        from src.mcp.server import get_task_status

        async def fake_api(method, path, **kwargs):
            return {
                "status": "completed",
                "message": "done",
                "result": {
                    "title": "测试视频",
                    "summary": "摘要",
                    "key_points": ["要点"],
                    "segments": [
                        {
                            "start_time": 0,
                            "end_time": 10,
                            "text": "分段内容",
                            "topic": "主题",
                        }
                    ],
                    "metadata": {"owner": "测试UP主"},
                },
            }

        with patch("src.mcp.server._api", new=fake_api):
            result = asyncio.run(get_task_status(task_id="task-1"))

        assert result["analysis"]["metadata"] == {"owner": "测试UP主"}

    def test_get_analysis_resource_includes_metadata(self):
        from src.mcp.server import get_analysis

        async def fake_completed_task(task_id):
            return {
                "title": "测试视频",
                "summary": "摘要",
                "key_points": ["要点"],
                "segments": [],
                "metadata": {"owner": "测试UP主"},
            }

        with patch("src.mcp.server._get_completed_task", new=fake_completed_task):
            payload = asyncio.run(get_analysis(task_id="task-1"))

        assert json.loads(payload)["metadata"] == {"owner": "测试UP主"}


class TestGenerateMindmap:
    def test_generate_mindmap_prefers_analysis_segments(self, tmp_path):
        from src.mcp.server import generate_mindmap

        class FakeRoot:
            def model_dump(self):
                return {"title": "root"}

        class FakeOutput:
            node_count = 1
            root = FakeRoot()

        captured = {}

        async def fake_api(method, path, **kwargs):
            return {
                "status": "completed",
                "message": "done",
                "result": {
                    "title": "测试视频",
                    "transcript": "原始转写不应优先使用",
                    "segments": [
                        {
                            "start_time": 0,
                            "end_time": 10,
                            "topic": "主题一",
                            "text": "结构化分段一",
                        }
                    ],
                    "output_dir": str(tmp_path),
                },
            }

        async def fake_generate_mindmap(text, title, depth="low", prompt_hint=""):
            captured["text"] = text
            captured["title"] = title
            captured["depth"] = depth
            captured["prompt_hint"] = prompt_hint
            return FakeOutput()

        with (
            patch("src.mcp.server._api", new=fake_api),
            patch("src.services.mindmap.generate_mindmap", new=fake_generate_mindmap),
            patch("src.services.mindmap.export_mindmap_to_files", return_value={}),
            patch("src.services.mindmap.render_mermaid", return_value="graph TD"),
        ):
            result = asyncio.run(
                generate_mindmap(task_id="task-1", depth="high", prompt_hint="聚焦主题")
            )

        assert result["node_count"] == 1
        assert result["depth"] == "high"
        assert captured["text"] == "主题一: 结构化分段一"
        assert captured["title"] == "测试视频"
        assert captured["depth"] == "high"
        assert captured["prompt_hint"] == "聚焦主题"
