from unittest.mock import patch

from src.core.processors.video import VideoProcessor


def test_get_cc_text_uses_page_specific_cid():
    processor = VideoProcessor()
    video_url = "https://www.bilibili.com/video/BV1xx411c7mD?p=3"
    cc_text = "x" * 220

    with (
        patch("src.mcp.cc_subtitle.extract_bvid_from_url", return_value="BV1xx411c7mD"),
        patch("src.mcp.cc_subtitle.extract_page_from_url", return_value=3),
        patch("src.mcp.cc_subtitle.get_cid_for_page_sync", return_value="333") as mock_cid,
        patch("src.mcp.cc_subtitle.check_cc_sync", return_value=cc_text) as mock_check,
    ):
        result_text, bvid = processor._get_cc_text(video_url)

    assert result_text == cc_text
    assert bvid == "BV1xx411c7mD"
    mock_cid.assert_called_once_with("BV1xx411c7mD", 3)
    mock_check.assert_called_once_with("BV1xx411c7mD", "333")


def test_get_cc_text_returns_bvid_when_cid_missing():
    processor = VideoProcessor()
    video_url = "https://www.bilibili.com/video/BV1xx411c7mD"

    with (
        patch("src.mcp.cc_subtitle.extract_bvid_from_url", return_value="BV1xx411c7mD"),
        patch("src.mcp.cc_subtitle.extract_page_from_url", return_value=1),
        patch("src.mcp.cc_subtitle.get_cid_for_page_sync", return_value=None),
        patch("src.mcp.cc_subtitle.check_cc_sync") as mock_check,
    ):
        result_text, bvid = processor._get_cc_text(video_url)

    assert result_text is None
    assert bvid == "BV1xx411c7mD"
    mock_check.assert_not_called()
