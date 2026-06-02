from unittest.mock import AsyncMock, patch

import pytest

from src.mcp.cc_subtitle import extract_bvid_from_url, extract_cc_text, has_usable_cc


def test_extract_cc_text_returns_clean_text():
    subtitle_json = {
        "body": [
            {"content": "第一句"},
            {"content": "第二句"},
            {"content": "第三句"},
        ]
    }

    assert extract_cc_text(subtitle_json) == "第一句 第二句 第三句"


def test_extract_cc_text_empty_body():
    assert extract_cc_text({"body": []}) == ""


def test_extract_cc_text_missing_content():
    subtitle_json = {"body": [{"from": 0}, {"content": "保留"}, {}]}

    assert extract_cc_text(subtitle_json) == "保留"


@pytest.mark.asyncio
@patch("src.mcp.cc_subtitle.download_cc_subtitle", new_callable=AsyncMock)
@patch("src.mcp.cc_subtitle.fetch_cc_subtitle_list", new_callable=AsyncMock)
async def test_has_usable_cc_returns_text_for_zh_subtitle(
    mock_fetch_cc_subtitle_list, mock_download_cc_subtitle
):
    expected_text = "中" * 220
    mock_fetch_cc_subtitle_list.return_value = [
        {"lang_key": "zh", "subtitle_url": "//example.com/subtitle.json"}
    ]
    mock_download_cc_subtitle.return_value = {
        "body": [{"content": expected_text[:110]}, {"content": expected_text[110:]}]
    }

    result = await has_usable_cc("BV1xx411c7mD", "12345")

    assert result == f"{expected_text[:110]} {expected_text[110:]}"


@pytest.mark.asyncio
@patch("src.mcp.cc_subtitle.fetch_cc_subtitle_list", new_callable=AsyncMock)
async def test_has_usable_cc_returns_none_for_non_chinese(mock_fetch_cc_subtitle_list):
    mock_fetch_cc_subtitle_list.return_value = [
        {"lang_key": "en", "subtitle_url": "//example.com/subtitle.json"}
    ]

    result = await has_usable_cc("BV1xx411c7mD", "12345")

    assert result is None


@pytest.mark.asyncio
@patch("src.mcp.cc_subtitle.download_cc_subtitle", new_callable=AsyncMock)
@patch("src.mcp.cc_subtitle.fetch_cc_subtitle_list", new_callable=AsyncMock)
async def test_has_usable_cc_returns_none_for_short_text(
    mock_fetch_cc_subtitle_list, mock_download_cc_subtitle
):
    mock_fetch_cc_subtitle_list.return_value = [
        {"lang_key": "zh-CN", "subtitle_url": "//example.com/subtitle.json"}
    ]
    mock_download_cc_subtitle.return_value = {"body": [{"content": "短文本" * 10}]}

    result = await has_usable_cc("BV1xx411c7mD", "12345")

    assert result is None


@pytest.mark.asyncio
@patch("src.mcp.cc_subtitle.fetch_cc_subtitle_list", new_callable=AsyncMock)
async def test_has_usable_cc_returns_none_when_no_subtitles(mock_fetch_cc_subtitle_list):
    mock_fetch_cc_subtitle_list.return_value = []

    result = await has_usable_cc("BV1xx411c7mD", "12345")

    assert result is None


def test_extract_bvid_from_url():
    url = "https://www.bilibili.com/video/BV1xx411c7mD?p=1&vd_source=test"

    assert extract_bvid_from_url(url) == "BV1xx411c7mD"


def test_extract_bvid_from_url_invalid():
    assert extract_bvid_from_url("https://www.example.com/video/123") is None
