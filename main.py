from src.Timer import Timer
from src.bilibili_downloader import download_bilibili_audio
from src.config import *
from src.extract_audio_text import extract_audio_text
from src.output_file_manager import move_output_files
from src.text_arrangement.polish_by_llm import polish_text
from src.text_arrangement.summary_by_llm import summarize_text
from src.text_arrangement.text_exporter import text_to_img_or_pdf


def main(local_audio_path: str = None):
    timer = Timer()

    if local_audio_path is None:
        video_url = input("请输入B站视频链接（例如：https://www.bilibili.com/video/BV1...）：\n")
        timer.start()
        print("正在下载音频...")
        audio_path = download_bilibili_audio(video_url, output_format='mp3', output_dir=DOWNLOAD_DIR)
        print(f"音频已下载到：{audio_path}", "用时：", timer.stop(), "秒")
    else:
        audio_path = local_audio_path
        print(f"使用已有音频：{audio_path}")

    audio_file_name = os.path.basename(audio_path).split(".")[0]

    timer.start()
    print("正在提取音频文本...")
    audio_text = extract_audio_text(input_audio_path=audio_path, model_type=ASR_MODEL)
    print("音频文本提取完成，用时：", timer.stop(), "秒")

    text_file_path = os.path.join(OUTPUT_DIR, "audio_transcription.txt")
    with open(text_file_path, "w", encoding="utf-8") as f:
        f.write(audio_text)
    print(f"音频文本已保存到：{text_file_path}")

    if not DISABLE_LLM_POLISH:
        timer.start()
        print("正在润色文本...")
        polished_text = polish_text(audio_text, api_service=LLM_SERVER, temperature=LLM_TEMPERATURE,
                                    split_len=SPLIT_LIMIT, max_tokens=LLM_MAX_TOKENS, debug_flag=DEBUG_FLAG,
                                    async_flag=ASYNC_FLAG)
        print("文本润色完成，用时：", timer.stop(), "秒")

        polish_text_file_path = os.path.join(OUTPUT_DIR, "polish_text.txt")
        with open(polish_text_file_path, "w", encoding="utf-8") as f:
            f.write(polished_text)
        print(f"润色后的文本已保存到：{polish_text_file_path}")
    else:
        polished_text = audio_text
        print("文本润色已跳过。")

    text_to_img_or_pdf(polished_text, title=audio_file_name, output_style=OUTPUT_STYLE, output_path=OUTPUT_DIR,
                       LLM_info=f'({LLM_SERVER}, 温度: {LLM_TEMPERATURE})', ASR_model=ASR_MODEL)

    if not DISABLE_LLM_SUMMARY:
        print("正在生成 Summary...")
        summary_text = summarize_text(txt=polished_text, api_server=SUMMARY_LLM_SERVER,
                                      temperature=SUMMARY_LLM_TEMPERATURE, max_tokens=SUMMARY_LLM_MAX_TOKENS,
                                      title=audio_file_name)
        with open(os.path.join(OUTPUT_DIR, "summary_text.md"), "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"文本摘要已保存到：{os.path.join(OUTPUT_DIR, 'summary_text.md')}")

        move_output_files(audio_file_name)
        print("所有操作完成。")


if __name__ == "__main__":
    main()
