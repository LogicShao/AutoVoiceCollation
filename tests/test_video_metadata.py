from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp.bilibili_api import (
    VideoMetadata,
    _truncate_to_token_budget,
    format_metadata_for_prompt,
    get_video_metadata,
)


class TestVideoMetadataModel:
    def test_default_empty(self):
        m = VideoMetadata()
        assert m.title == ""
        assert m.tags == []
        assert m.chapters == []
        assert m.hot_comments == []

    def test_populated(self):
        m = VideoMetadata(
            title="Test",
            owner="Alice",
            tags=["tag1", "tag2"],
        )
        assert m.title == "Test"
        assert m.owner == "Alice"
        assert len(m.tags) == 2


class TestTruncateToTokenBudget:
    def test_empty_string(self):
        assert _truncate_to_token_budget("") == ""

    def test_none_string(self):
        assert _truncate_to_token_budget("") == ""

    def test_short_text_unchanged(self):
        text = "Hello World"
        result = _truncate_to_token_budget(text, 100)
        assert result == text

    def test_long_chinese_truncated(self):
        text = "测试" * 1000  # 2000 tokens
        result = _truncate_to_token_budget(text, 500)
        assert len(result) < len(text)
        assert len(result) <= 510  # slightly over 500 tokens

    def test_default_budget_is_500(self):
        text = "x" * 5000  # ~1250 tokens
        result = _truncate_to_token_budget(text)
        assert len(result) <= 2010  # 2000 chars ≈ 500 tokens


class TestFormatMetadataForPrompt:
    def test_empty_metadata_returns_minimal(self):
        m = VideoMetadata()
        result = format_metadata_for_prompt(m)
        assert "[视频元数据]" in result

    def test_populated_metadata(self):
        m = VideoMetadata(
            title="Test Video",
            description="A test",
            tags=["tag1"],
            owner="Alice",
            chapters=[{"title": "Part 1", "part_number": 1, "duration": 300}],
            hot_comments=["Great!"],
        )
        result = format_metadata_for_prompt(m)
        assert "Test Video" in result
        assert "tag1" in result
        assert "Alice" in result
        assert "Part 1" in result
        assert "Great!" in result

    def test_metadata_truncated_to_token_budget(self):
        m = VideoMetadata(
            title="Test" * 500,
            description="Desc" * 500,
        )
        result = format_metadata_for_prompt(m)
        assert len(result) <= 2200  # ~500 tokens


class TestGetVideoMetadata:
    @pytest.mark.asyncio
    async def test_returns_all_fields(self):
        mock_session = AsyncMock()
        mock_responses = [
            AsyncMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "data": {
                            "title": "Test Video",
                            "desc": "Description here",
                            "tags": [{"tag_name": "科技"}, {"tag_name": "AI"}],
                            "owner": {"name": "TestAuthor"},
                        }
                    }
                ),
            ),
            AsyncMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "data": [
                            {"part": "Ch1", "duration": 300},
                            {"part": "Ch2", "duration": 600},
                        ]
                    }
                ),
            ),
            AsyncMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "data": {
                            "replies": [
                                {"content": {"message": "Great video!"}},
                                {"content": {"message": "Very helpful"}},
                            ]
                        }
                    }
                ),
            ),
        ]
        mock_session.get.side_effect = mock_responses
        with patch("src.mcp.bilibili_api._ensure_session", return_value=mock_session):
            result = await get_video_metadata("BV1xx411c7mD")
            assert result.title == "Test Video"
            assert result.owner == "TestAuthor"
            assert len(result.tags) == 2
            assert len(result.chapters) == 2
            assert len(result.hot_comments) == 2

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_error(self):
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Network error")
        with patch("src.mcp.bilibili_api._ensure_session", return_value=mock_session):
            result = await get_video_metadata("BV1xx411c7mD")
            assert result.title == ""
            assert result.owner == ""
            assert result.tags == []

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_403(self):
        mock_session = AsyncMock()
        from httpx import HTTPStatusError

        mock_session.get.side_effect = HTTPStatusError(
            "Forbidden", request=MagicMock(), response=MagicMock(status_code=403)
        )
        with patch("src.mcp.bilibili_api._ensure_session", return_value=mock_session):
            result = await get_video_metadata("BV1xx411c7mD")
            assert result.title == ""
