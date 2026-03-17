"""处理历史管理单元测试。"""

from src.core.history import ProcessHistoryManager


def _reset_history_manager() -> None:
    ProcessHistoryManager._instance = None
    ProcessHistoryManager._initialized = False


def _make_history_manager(history_file):
    _reset_history_manager()
    return ProcessHistoryManager(str(history_file))


def test_extract_bilibili_id_supports_bv_and_av(tmp_path):
    manager = _make_history_manager(tmp_path / ".process_history.json")

    assert (
        manager.extract_bilibili_id("https://www.bilibili.com/video/BV1xx411c7mD") == "BV1xx411c7mD"
    )
    assert manager.extract_bilibili_id("https://b23.tv/BV1xx411c7mD") == "BV1xx411c7mD"
    assert manager.extract_bilibili_id("https://www.bilibili.com/video/av12345678") == "av12345678"
    assert manager.extract_bilibili_id("https://example.com/video") is None

    _reset_history_manager()


def test_generate_file_identifier_is_stable_for_missing_file(tmp_path):
    manager = _make_history_manager(tmp_path / ".process_history.json")

    missing_file = tmp_path / "missing_audio.mp3"
    first_identifier = manager.generate_file_identifier(str(missing_file))
    second_identifier = manager.generate_file_identifier(str(missing_file))

    assert first_identifier == second_identifier
    assert len(first_identifier) == 16

    _reset_history_manager()


def test_create_record_from_bilibili_updates_existing_record(tmp_path):
    manager = _make_history_manager(tmp_path / ".process_history.json")

    first_record = manager.create_record_from_bilibili(
        url="https://www.bilibili.com/video/BV1xx411c7mD",
        title="第一次处理",
        output_dir="out/test_video",
        config={"asr_model": "paraformer"},
        outputs={"audio_transcription": "out/test_video/audio.txt"},
    )
    manager.create_record_from_bilibili(
        url="https://www.bilibili.com/video/BV1xx411c7mD",
        title="第二次处理",
        output_dir="out/test_video_retry",
        config={"asr_model": "sense_voice"},
        outputs={"audio_transcription": "out/test_video_retry/audio.txt"},
    )

    stored_record = manager.get_record(first_record.identifier)

    assert stored_record is not None
    assert stored_record.process_count == 2
    assert stored_record.output_dir == "out/test_video_retry"
    assert stored_record.config["asr_model"] == "sense_voice"
    assert len(manager.get_all_records()) == 1

    _reset_history_manager()


def test_create_local_records_updates_statistics(tmp_path):
    manager = _make_history_manager(tmp_path / ".process_history.json")

    audio_file = tmp_path / "sample.mp3"
    video_file = tmp_path / "sample.mp4"
    audio_file.write_bytes(b"audio")
    video_file.write_bytes(b"video")

    audio_record = manager.create_record_from_local_file(
        file_path=str(audio_file),
        file_type="local_audio",
        title="音频文件",
        output_dir="out/test_audio",
        config={"llm_api": "deepseek"},
        outputs={"polish_text": "out/test_audio/polish.txt"},
    )
    video_record = manager.create_record_from_local_file(
        file_path=str(video_file),
        file_type="local_video",
        title="视频文件",
        output_dir="out/test_video",
        config={"llm_api": "gemini"},
        outputs={"polish_text": "out/test_video/polish.txt"},
    )

    stats = manager.get_statistics()

    assert audio_record.record_type == "local_audio"
    assert video_record.record_type == "local_video"
    assert stats["total_records"] == 2
    assert stats["local_audios"] == 1
    assert stats["local_videos"] == 1
    assert stats["bilibili_videos"] == 0
    assert stats["total_processes"] == 2

    _reset_history_manager()
