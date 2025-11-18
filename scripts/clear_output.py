import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.output_file_manager import remove_files, clean_directory
from src.config import OUTPUT_DIR, DOWNLOAD_DIR, TEMP_DIR

if __name__ == '__main__':
    clean_directory(OUTPUT_DIR)
    clean_directory(DOWNLOAD_DIR)
    clean_directory(TEMP_DIR)
    remove_files(['output.txt'])
