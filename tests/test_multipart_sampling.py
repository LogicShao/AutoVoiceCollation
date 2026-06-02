from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from src.core.processors.multi_part_video import MultiPartVideoProcessor


@dataclass
class MockBiliVideoPart:
    part_number: int
    title: str
    video_id: str
    url: str
    duration: int = 0


def make_part(n, cid="", url=""):
    return MockBiliVideoPart(
        part_number=n,
        title=f"Part {n}",
        video_id=cid or str(n),
        url=url or f"https://www.bilibili.com/video/BV1xx411c7mD?p={n}",
    )


@pytest.fixture
def processor():
    return MultiPartVideoProcessor()


class TestDeterministicSeed:
    def test_same_bvid_produces_same_seed(self, processor):
        s1 = processor._deterministic_seed("BV1xx411c7mD")
        s2 = processor._deterministic_seed("BV1xx411c7mD")
        assert s1 == s2

    def test_different_bvid_produces_different_seed(self, processor):
        s1 = processor._deterministic_seed("BV1xx411c7mD")
        s2 = processor._deterministic_seed("BV1xx411c7mE")
        assert s1 != s2


class TestSampleParts:
    def test_random_n_samples_exact_count(self, processor):
        parts = [make_part(i) for i in range(1, 11)]
        sampled = processor._sample_parts(parts, 3, "https://www.bilibili.com/video/BV1xx411c7mD")
        assert len(sampled) == 3

    def test_random_n_exceeds_total_returns_all(self, processor):
        parts = [make_part(i) for i in range(1, 4)]
        sampled = processor._sample_parts(parts, 50, "https://www.bilibili.com/video/BV1xx411c7mD")
        assert len(sampled) == 3

    def test_random_n_is_deterministic(self, processor):
        parts = [make_part(i) for i in range(1, 11)]
        s1 = processor._sample_parts(parts, 3, "https://www.bilibili.com/video/BV1xx411c7mD")
        s2 = processor._sample_parts(parts, 3, "https://www.bilibili.com/video/BV1xx411c7mD")
        assert [p.part_number for p in s1] == [p.part_number for p in s2]

    def test_head_middle_tail(self, processor):
        parts = [make_part(i) for i in range(1, 11)]
        sampled = processor._sample_parts(
            parts, "head+middle+tail", "https://www.bilibili.com/video/BV1xx"
        )
        assert len(sampled) == 3
        assert sampled[0].part_number == 1
        assert sampled[1].part_number == 5
        assert sampled[2].part_number == 10

    def test_head_middle_tail_less_than_3(self, processor):
        parts = [make_part(1), make_part(2)]
        sampled = processor._sample_parts(
            parts, "head+middle+tail", "https://www.bilibili.com/video/BV1xx"
        )
        assert len(sampled) == 2

    def test_none_returns_all(self, processor):
        parts = [make_part(i) for i in range(1, 6)]
        sampled = processor._sample_parts(parts, None, "https://www.bilibili.com/video/BV1xx")
        assert len(sampled) == 5

    def test_cc_only_filters_cc_parts(self, processor):
        parts = [make_part(1, "101"), make_part(2, "102"), make_part(3, "103")]
        with patch("src.mcp.cc_subtitle.check_cc_sync", return_value="cc text here"):
            sampled = processor._sample_parts(
                parts, "cc_only", "https://www.bilibili.com/video/BV1xx"
            )
            assert len(sampled) == 3

    def test_cc_only_returns_empty_when_no_cc(self, processor):
        parts = [make_part(1, "201"), make_part(2, "202")]
        with patch("src.mcp.cc_subtitle.check_cc_sync", return_value=None):
            sampled = processor._sample_parts(
                parts, "cc_only", "https://www.bilibili.com/video/BV1xx"
            )
            assert len(sampled) == 0

    def test_part_cc_text_resolves_non_numeric_video_id_by_page(self, processor):
        part = make_part(2, "BV1xx411c7mD_p2")

        with (
            patch("src.mcp.cc_subtitle.get_cid_for_page_sync", return_value="222") as mock_cid,
            patch("src.mcp.cc_subtitle.check_cc_sync", return_value="cc text here") as mock_check,
        ):
            cc_text = processor._get_part_cc_text(part)

        assert cc_text == "cc text here"
        mock_cid.assert_called_once_with("BV1xx411c7mD", 2)
        mock_check.assert_called_once_with("BV1xx411c7mD", "222")

    def test_part_cc_text_uses_cache(self, processor):
        part = make_part(1, "101")

        with patch("src.mcp.cc_subtitle.check_cc_sync", return_value="cc text here") as mock_check:
            first = processor._get_part_cc_text(part)
            second = processor._get_part_cc_text(part)

        assert first == second == "cc text here"
        mock_check.assert_called_once_with("BV1xx411c7mD", "101")

    def test_empty_parts_returns_empty(self, processor):
        sampled = processor._sample_parts([], 3, "https://www.bilibili.com/video/BV1xx")
        assert len(sampled) == 0
