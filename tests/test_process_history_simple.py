"""
处理历史管理系统测试脚本（简化版，无emoji）

这个脚本演示了如何使用处理历史管理功能。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core_process_utils import (
    check_bilibili_processed,
    record_bilibili_process,
    record_local_file_process,
)
from src.process_history import get_history_manager


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("测试 1: 基本功能测试")
    print("=" * 60)

    history_manager = get_history_manager()

    # 测试B站视频ID提取
    test_urls = [
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "https://b23.tv/BV1xx411c7mD",
        "https://www.bilibili.com/video/av12345678",
    ]

    print("\n[TEST] 测试URL解析:")
    for url in test_urls:
        vid = history_manager.extract_bilibili_id(url)
        print(f"  {url}")
        print(f"  -> 提取ID: {vid}\n")

    # 测试文件标识符生成
    print("\n[TEST] 测试文件标识符生成:")
    test_file = str(project_root / "README.md")
    identifier = history_manager.generate_file_identifier(test_file)
    print(f"  文件: {test_file}")
    print(f"  -> 标识符: {identifier}\n")


def test_record_creation():
    """测试创建处理记录"""
    print("=" * 60)
    print("测试 2: 创建处理记录")
    print("=" * 60)

    # 测试B站视频记录
    print("\n[TEST] 创建B站视频处理记录:")
    test_config = {
        "asr_model": "paraformer",
        "llm_api": "deepseek-chat",
        "temperature": 0.1,
        "max_tokens": 6000,
    }
    test_outputs = {
        "audio_transcription": "out/test_video/audio_transcription.txt",
        "polish_text": "out/test_video/polish_text.txt",
        "summary_text": "out/test_video/summary_text.md",
    }

    record = record_bilibili_process(
        video_url="https://www.bilibili.com/video/BV1xx411c7mD",
        title="测试视频标题",
        output_dir="out/test_video",
        config=test_config,
        outputs=test_outputs,
    )

    if record:
        print("  [OK] 记录已创建")
        print(f"     ID: {record.identifier}")
        print(f"     标题: {record.title}")
        print(f"     处理时间: {record.last_processed}")
        print(f"     处理次数: {record.process_count}")
    else:
        print("  [FAIL] 记录创建失败")


def test_history_check():
    """测试历史检查"""
    print("\n" + "=" * 60)
    print("测试 3: 历史检查")
    print("=" * 60)

    test_url = "https://www.bilibili.com/video/BV1xx411c7mD"

    print(f"\n[TEST] 检查视频: {test_url}")
    record = check_bilibili_processed(test_url)

    if record:
        print("  [OK] 找到处理记录:")
        print(f"     标题: {record.title}")
        print(f"     输出目录: {record.output_dir}")
        print(f"     上次处理: {record.last_processed}")
        print(f"     处理次数: {record.process_count}")
        print("     使用配置:")
        for key, value in record.config.items():
            print(f"       - {key}: {value}")
    else:
        print("  [INFO] 未找到处理记录")


def test_statistics():
    """测试统计功能"""
    print("\n" + "=" * 60)
    print("测试 4: 统计信息")
    print("=" * 60)

    history_manager = get_history_manager()
    stats = history_manager.get_statistics()

    print("\n[STAT] 处理历史统计:")
    print(f"  总记录数: {stats['total_records']}")
    print(f"  B站视频: {stats['bilibili_videos']}")
    print(f"  本地音频: {stats['local_audios']}")
    print(f"  本地视频: {stats['local_videos']}")
    print(f"  总处理次数: {stats['total_processes']}")


def test_record_listing():
    """测试记录列表"""
    print("\n" + "=" * 60)
    print("测试 5: 记录列表")
    print("=" * 60)

    history_manager = get_history_manager()
    records = history_manager.get_all_records()

    if not records:
        print("\n  [INFO] 暂无处理记录")
        return

    print(f"\n[LIST] 共有 {len(records)} 条记录:")
    for i, record in enumerate(records[:5], 1):  # 只显示前5条
        print(f"\n  {i}. {record.title}")
        print(f"     类型: {record.record_type}")
        print(f"     ID: {record.identifier}")
        print(f"     处理时间: {record.last_processed}")
        print(f"     处理次数: {record.process_count}")
        print(f"     输出目录: {record.output_dir}")

    if len(records) > 5:
        print(f"\n  ... 还有 {len(records) - 5} 条记录")


def test_duplicate_processing():
    """测试重复处理"""
    print("\n" + "=" * 60)
    print("测试 6: 重复处理记录")
    print("=" * 60)

    # 再次处理同一个视频
    print("\n[TEST] 模拟重复处理同一个视频:")
    test_config = {
        "asr_model": "sense_voice",
        "llm_api": "gemini-2.0-flash",
        "temperature": 0.3,
        "max_tokens": 8000,
    }
    test_outputs = {
        "audio_transcription": "out/test_video_1/audio_transcription.txt",
        "polish_text": "out/test_video_1/polish_text.txt",
    }

    record = record_bilibili_process(
        video_url="https://www.bilibili.com/video/BV1xx411c7mD",
        title="测试视频标题",
        output_dir="out/test_video_1",
        config=test_config,
        outputs=test_outputs,
    )

    if record:
        print("  [OK] 记录已更新")
        print(f"     处理次数: {record.process_count} (应该增加了)")
        print(f"     最新输出目录: {record.output_dir}")
        print(
            f"     最新配置: ASR={record.config.get('asr_model')}, LLM={record.config.get('llm_api')}"
        )
    else:
        print("  [FAIL] 记录更新失败")


def test_local_file_record():
    """测试本地文件记录"""
    print("\n" + "=" * 60)
    print("测试 7: 本地文件处理记录")
    print("=" * 60)

    print("\n[TEST] 创建本地音频文件处理记录:")
    test_file = str(project_root / "test_audio.mp3")  # 假设的文件路径

    record = record_local_file_process(
        file_path=test_file,
        file_type="local_audio",
        title="测试音频文件",
        output_dir="out/test_audio",
        config={
            "asr_model": "paraformer",
            "llm_api": "deepseek-chat",
            "temperature": 0.1,
            "max_tokens": 6000,
        },
        outputs={
            "audio_transcription": "out/test_audio/audio_transcription.txt",
            "polish_text": "out/test_audio/polish_text.txt",
        },
    )

    if record:
        print("  [OK] 本地文件记录已创建")
        print(f"     ID: {record.identifier}")
        print(f"     类型: {record.record_type}")
        print(f"     文件: {test_file}")
    else:
        print("  [FAIL] 本地文件记录创建失败")


def main():
    """主测试函数"""
    print("\n")
    print("+" + "=" * 58 + "+")
    print("|" + " " * 15 + "处理历史管理系统测试" + " " * 23 + "|")
    print("+" + "=" * 58 + "+")
    print()

    try:
        # 运行所有测试
        test_basic_functionality()
        test_record_creation()
        test_history_check()
        test_statistics()
        test_record_listing()
        test_duplicate_processing()
        test_local_file_record()

        print("\n" + "=" * 60)
        print("[SUCCESS] 所有测试完成！")
        print("=" * 60)
        print()

        # 显示历史文件位置
        history_manager = get_history_manager()
        print(f"[INFO] 历史文件位置: {history_manager.history_file}")
        if history_manager.history_file.exists():
            print(f"       文件大小: {history_manager.history_file.stat().st_size} 字节")
        print()

    except Exception as e:
        print(f"\n[ERROR] 测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
