from src.services.download.bilibili_downloader import (
    BILIBILI_HTTP_HEADERS,
    _build_ydl_options,
    _is_bilibili_url,
)


def test_is_bilibili_url_matches_main_and_short_domains():
    assert _is_bilibili_url("https://www.bilibili.com/video/BV11pVM6iERu")
    assert _is_bilibili_url("https://m.bilibili.com/video/BV11pVM6iERu")
    assert _is_bilibili_url("https://b23.tv/example")


def test_is_bilibili_url_rejects_other_domains():
    assert not _is_bilibili_url("https://www.youtube.com/watch?v=jNQXAC9IVRw")
    assert not _is_bilibili_url("https://example.com/bilibili.com/video/BV11pVM6iERu")


def test_build_ydl_options_adds_bilibili_headers():
    options = _build_ydl_options(
        "https://www.bilibili.com/video/BV11pVM6iERu",
        quiet=True,
        noplaylist=True,
    )

    assert options["quiet"] is True
    assert options["noplaylist"] is True
    assert options["http_headers"]["Referer"] == BILIBILI_HTTP_HEADERS["Referer"]
    assert "Mozilla/5.0" in options["http_headers"]["User-Agent"]


def test_build_ydl_options_keeps_existing_headers_precedence():
    options = _build_ydl_options(
        "https://www.bilibili.com/video/BV11pVM6iERu",
        http_headers={"User-Agent": "Custom-UA", "Cookie": "SESSDATA=test"},
    )

    assert options["http_headers"]["User-Agent"] == "Custom-UA"
    assert options["http_headers"]["Cookie"] == "SESSDATA=test"
    assert options["http_headers"]["Referer"] == BILIBILI_HTTP_HEADERS["Referer"]


def test_build_ydl_options_does_not_add_bilibili_headers_for_youtube():
    options = _build_ydl_options("https://www.youtube.com/watch?v=jNQXAC9IVRw", quiet=True)

    assert options == {"quiet": True}
