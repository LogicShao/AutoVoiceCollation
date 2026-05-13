import asyncio

import pytest


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
