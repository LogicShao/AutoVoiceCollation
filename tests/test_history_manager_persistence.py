"""处理历史持久化测试。"""

from types import SimpleNamespace

from src.core.history import ProcessHistoryManager, get_history_manager
from src.core.history import manager as history_manager_module


def _reset_history_manager() -> None:
    ProcessHistoryManager._instance = None
    ProcessHistoryManager._initialized = False


def test_get_history_manager_uses_configured_output_dir(monkeypatch, tmp_path):
    _reset_history_manager()
    fake_config = SimpleNamespace(paths=SimpleNamespace(output_dir=tmp_path))
    monkeypatch.setattr(history_manager_module, "get_config", lambda: fake_config)

    manager = get_history_manager()

    assert manager.history_file == tmp_path / ".process_history.json"

    _reset_history_manager()


def test_history_records_persist_after_singleton_reset(tmp_path):
    history_file = tmp_path / ".process_history.json"
    _reset_history_manager()
    manager = ProcessHistoryManager(str(history_file))
    manager.create_record_from_bilibili(
        url="https://www.bilibili.com/video/BV1A84y1x7mD",
        title="持久化测试",
        output_dir="out/persistence",
        config={"llm_api": "deepseek"},
        outputs={"summary_text": "out/persistence/summary.md"},
    )

    _reset_history_manager()
    reloaded_manager = ProcessHistoryManager(str(history_file))
    record = reloaded_manager.get_record("BV1A84y1x7mD")

    assert record is not None
    assert record.title == "持久化测试"
    assert record.output_dir == "out/persistence"
    assert record.outputs["summary_text"] == "out/persistence/summary.md"

    _reset_history_manager()
