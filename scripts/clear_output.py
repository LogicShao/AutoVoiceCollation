import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.export import remove_files, clean_directory
from src.utils.config import get_config

if __name__ == '__main__':
    config = get_config()
    clean_directory(str(config.paths.output_dir))
    clean_directory(str(config.paths.download_dir))
    clean_directory(str(config.paths.temp_dir))
    remove_files(['output.txt'])
