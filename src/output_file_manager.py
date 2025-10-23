import os
import shutil

from config import OUTPUT_DIR


def copy_output_files(audio_name: str):
    """
    将输出文件复制到子目录
    """
    destination_dir = os.path.join(OUTPUT_DIR, audio_name)
    os.makedirs(destination_dir, exist_ok=True)

    file_names = ['audio_transcription.txt', 'polish_text.txt', 'summary_text.md', 'output.pdf',
                  'debug_polished_text.txt']

    for file_name in file_names:
        source_file = os.path.join(OUTPUT_DIR, file_name)
        if os.path.exists(source_file):
            shutil.copy(source_file, destination_dir)
        else:
            print(f"警告：文件 {source_file} 不存在，无法复制。")

    return destination_dir


def move_output_files(audio_name: str):
    """
    将输出文件整理到子目录
    """
    destination_dir = os.path.join(OUTPUT_DIR, audio_name)
    if os.path.exists(destination_dir):
        index = 1
        while os.path.exists(destination_dir + f"_{index}"):
            index += 1
        destination_dir = destination_dir + f"_{index}"
    os.makedirs(destination_dir)

    file_names = ['audio_transcription.txt', 'polish_text.txt', 'summary_text.md', 'output.pdf',
                  'debug_polished_text.txt']

    for file_name in file_names:
        source_file = os.path.join(OUTPUT_DIR, file_name)
        if os.path.exists(source_file):
            shutil.move(source_file, destination_dir)
        else:
            print(f"警告：文件 {source_file} 不存在，无法移动。")

    return destination_dir


def clean_directory(directory_path: str):
    """
    清理指定目录下的所有文件和子目录。
    如果目录不存在，则不执行任何操作。
    """
    print(f"正在检查目录: {directory_path}")
    if os.path.exists(directory_path):
        print(f"找到目录 '{directory_path}'，正在清理...")
        try:
            # 移除整个目录树，包括目录本身和其中的所有文件/子目录
            shutil.rmtree(directory_path)
            print(f"成功清理目录: {directory_path}")
        except OSError as e:
            print(f"错误：清理目录 '{directory_path}' 失败: {e}")
        except Exception as e:
            print(f"清理目录 '{directory_path}' 时发生未知错误: {e}")
    else:
        print(f"目录 '{directory_path}' 不存在，无需清理。")


def remove_files(file_paths: list):
    """
    删除指定的文件列表。
    如果文件不存在，则不执行任何操作。
    """
    for file_path in file_paths:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"成功删除文件: {file_path}")
            except OSError as e:
                print(f"错误：删除文件 '{file_path}' 失败: {e}")
            except Exception as e:
                print(f"删除文件 '{file_path}' 时发生未知错误: {e}")
        else:
            print(f"文件 '{file_path}' 不存在，无需删除。")
