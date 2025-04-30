import argparse
import glob
import os
import shutil

from .config import OUTPUT_DIR, DOWNLOAD_DIR


def display_api_key(api_key: str, front_display_num: int = 6, back_display_num: int = 4) -> str:
    """
    显示 API 密钥的部分内容，前后各显示指定数量的字符。
    :param api_key: API 密钥
    :param front_display_num: 前面显示的字符数
    :param back_display_num: 后面显示的字符数
    :return: 显示的 API 密钥
    """
    if len(api_key) <= front_display_num + back_display_num:
        return api_key
    else:
        return api_key[:front_display_num] + '*' * (len(api_key) - front_display_num -
                                                    back_display_num) + api_key[-back_display_num:]


def copy_output_files(audio_name: str):
    """
    将输出文件整理到子目录
    """
    destination_dir = os.path.join(OUTPUT_DIR, audio_name)
    os.makedirs(destination_dir, exist_ok=True)

    txt_files = glob.glob(os.path.join(OUTPUT_DIR, "*.txt"))
    pdf_file = os.path.join(OUTPUT_DIR, "output.pdf")

    for file in txt_files:
        shutil.copy2(file, destination_dir)
    if os.path.exists(pdf_file):
        shutil.copy2(pdf_file, destination_dir)

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
            # 清理后重新创建空目录，保持目录结构存在（可选）
            # os.makedirs(directory_path)
            # print(f"重新创建了空目录: {directory_path}")
        except OSError as e:
            print(f"错误：清理目录 '{directory_path}' 失败: {e}")
        except Exception as e:
            print(f"清理目录 '{directory_path}' 时发生未知错误: {e}")
    else:
        print(f"目录 '{directory_path}' 不存在，无需清理。")


def main():
    """
    解析命令行参数并执行清理操作。
    """
    parser = argparse.ArgumentParser(description="清理指定目录下的文件。")

    parser.add_argument("--clean-output", action="store_true", help="清理OUTPUT_DIR")
    parser.add_argument("--clean-download", action="store_true", help="清理DOWNLOAD_DIR")
    parser.add_argument("--all", action="store_true", help="清理所有目录 (默认)")

    # 对于初步功能，我们不需要额外的参数，直接执行清理操作
    # 如果需要基于参数进行有条件的清理，可以在这里解析args，并在下面判断

    args = parser.parse_args()

    print("\n--- 开始清理 ---")

    if args.clean_output:
        clean_directory(OUTPUT_DIR)
    elif args.clean_download:
        clean_directory(DOWNLOAD_DIR)
    elif args.all:
        clean_directory(OUTPUT_DIR)
        clean_directory(DOWNLOAD_DIR)
    else:
        print("未指定清理选项。")

    print("--- 清理完成 ---")
