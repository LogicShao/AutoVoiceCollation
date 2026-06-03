import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.export.file_manager import clean_directory
from src.core.output_status import scan_output_cache
from src.utils.config import get_config


def main() -> None:
    parser = argparse.ArgumentParser(description="扫描或清理运行时输出缓存。")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际删除 output/download/temp 目录；默认只输出 dry-run 扫描结果。",
    )
    args = parser.parse_args()

    config = get_config()
    if not args.execute:
        scan = scan_output_cache(config.paths.output_dir)
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "output_dir": str(config.paths.output_dir),
                    "partial_directories": scan["partial_directories"],
                    "duplicate_groups": scan["duplicate_groups"],
                    "cleanup_candidates": scan["cleanup_candidates"],
                    "total_cache_size": scan["total_cache_size"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    clean_directory(str(config.paths.output_dir))
    clean_directory(str(config.paths.download_dir))
    clean_directory(str(config.paths.temp_dir))


if __name__ == "__main__":
    main()
