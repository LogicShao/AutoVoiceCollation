import os

from config import *
from extract_audio_text import extract_audio_text
from get_audio import download_bilibili_audio
from src.Timer import Timer
from src.text_arrangement.polish_by_llm.polish_by_llm import polish_text
from src.text_arrangement.text2img import text_to_image


def main(prev_audio_path: str = None):
    timer = Timer()

    if prev_audio_path is None:
        video_url = input("请输入B站视频链接（例如：https://www.bilibili.com/video/BV1...）：\n")
        timer.start()
        print("正在下载音频...")
        audio_path = download_bilibili_audio(video_url, output_format='mp3', output_dir=DOWNLOAD_DIR)
        print(f"音频已下载到：{audio_path}", "用时：", timer.stop(), "秒")
    else:
        audio_path = prev_audio_path
        print(f"使用已有音频：{audio_path}")

    timer.start()
    print("正在提取音频文本...")
    audio_text = extract_audio_text(audio_path, language="auto")
    print("音频文本提取完成，用时：", timer.stop(), "秒")

    text_file_path = os.path.join(OUTPUT_DIR, "audio_transcription.txt")
    with open(text_file_path, "w", encoding="utf-8") as f:
        f.write(audio_text)
    print(f"音频文本已保存到：{text_file_path}")

    timer.start()
    print("正在润色文本...")
    polished_text = polish_text(audio_text)
    print("文本润色完成，用时：", timer.stop(), "秒")

    polish_text_file_path = os.path.join(OUTPUT_DIR, "polish_text.txt")
    with open(polish_text_file_path, "w", encoding="utf-8") as f:
        f.write(polished_text)
    print(f"润色后的文本已保存到：{polish_text_file_path}")

    print("正在保存为图片...")
    image_path = text_to_image(polished_text, output_path=OUTPUT_DIR)
    print(f"文本已保存为图片：{image_path}")


if __name__ == "__main__":
    main(
        prev_audio_path=r"../download/【主义主义】形而上学（2）——古代贵族的精神冒险，背景性的符号秩序与它自己的对立，比下（形而下学）有余，比上（观念论）不足.mp3")
