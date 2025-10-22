import argparse
import sys

from src.Timer import Timer
from src.bilibili_downloader import download_bilibili_audio, BiliVideoFile, new_local_bili_file
from src.config import *
from src.core_process import (
    process_multiple_urls, process_subtitles, upload_audio, bilibili_video_download_process
)
from src.extract_audio_text import extract_audio_text
from src.text_arrangement.polish_by_llm import polish_text
from src.text_arrangement.summary_by_llm import summarize_text
from src.text_arrangement.text_exporter import text_to_img_or_pdf
from src.logger import configure_third_party_loggers

# Configure third-party loggers early using configured level (reduces noisy INFO from modelscope/funasr/etc.)
configure_third_party_loggers(log_level=THIRD_PARTY_LOG_LEVEL)


def cli():
    parser = argparse.ArgumentParser(description="音频/视频识别与文本整理工具 CLI")
    subparsers = parser.add_subparsers(dest="command")

    # 单文件处理
    single_parser = subparsers.add_parser("single", help="处理本地音频或B站视频链接")
    single_parser.add_argument("--audio", type=str, help="本地音频文件路径")
    single_parser.add_argument("--video", type=str, help="本地视频文件路径")
    single_parser.add_argument("--bili", type=str, help="B站视频链接")
    single_parser.add_argument("--llm_api", type=str, default=LLM_SERVER, help="LLM服务地址")
    single_parser.add_argument("--temperature", type=float, default=LLM_TEMPERATURE, help="LLM温度")
    single_parser.add_argument("--max_tokens", type=int, default=LLM_MAX_TOKENS, help="LLM最大tokens")

    # 批量处理
    batch_parser = subparsers.add_parser("batch", help="批量处理B站视频链接")
    batch_parser.add_argument("--url_file", type=str, required=True, help="包含多个B站链接的txt文件，每行一个")
    batch_parser.add_argument("--llm_api", type=str, default=LLM_SERVER, help="LLM服务地址")
    batch_parser.add_argument("--temperature", type=float, default=LLM_TEMPERATURE, help="LLM温度")
    batch_parser.add_argument("--max_tokens", type=int, default=LLM_MAX_TOKENS, help="LLM最大tokens")

    # 字幕添加
    subtitle_parser = subparsers.add_parser("subtitle", help="为本地视频添加字幕")
    subtitle_parser.add_argument("--video", type=str, required=True, help="本地视频文件路径")

    args = parser.parse_args()

    if args.command == "single":
        if args.audio:
            print("处理本地音频...")
            result = upload_audio(args.audio, args.llm_api, args.temperature, args.max_tokens)
            print("输出:", result)
        elif args.video:
            print("提取视频音频并处理...")
            from src.bilibili_downloader import extract_audio_from_video
            audio_path = extract_audio_from_video(args.video)
            result = upload_audio(audio_path, args.llm_api, args.temperature, args.max_tokens)
            print("输出:", result)
        elif args.bili:
            print("处理B站视频链接...")
            result = bilibili_video_download_process(args.bili, args.llm_api, args.temperature, args.max_tokens)
            print("输出:", result)
        else:
            print("请指定 --audio、--video 或 --bili 参数。")
    elif args.command == "batch":
        with open(args.url_file, "r", encoding="utf-8") as f:
            urls = f.read()
        print("批量处理B站链接...")
        result = process_multiple_urls(urls, args.llm_api, args.temperature, args.max_tokens)
        print("输出:", result)
    elif args.command == "subtitle":
        print("为视频添加字幕...")
        result = process_subtitles(args.video)
        print("输出:", result)
    else:
        parser.print_help()


def main(local_audio_path: str = None):
    timer = Timer()

    if local_audio_path is None:
        video_url = input("请输入B站视频链接（例如：https://www.bilibili.com/video/BV1...）：\n")
        timer.start()
        print("正在下载音频...")
        audio_file: BiliVideoFile = download_bilibili_audio(video_url, output_format='mp3', output_dir=DOWNLOAD_DIR)
        print(f"音频已下载到：{audio_file.path}", "用时：", timer.stop(), "秒")
    else:
        audio_file: BiliVideoFile = new_local_bili_file(local_audio_path)
        print(f"使用已有音频：{audio_file}")

    timer.start()
    print("正在提取音频文本...")
    audio_text = extract_audio_text(input_audio_path=audio_file.path, model_type=ASR_MODEL)
    print("音频文本提取完成，用时：", timer.stop(), "秒")

    output_dir = os.path.join(OUTPUT_DIR, audio_file.title)
    os.makedirs(output_dir, exist_ok=True)

    text_file_path = os.path.join(output_dir, "audio_transcription.txt")
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

        polish_text_file_path = os.path.join(output_dir, "polish_text.txt")
        audio_file.save_in_text(polished_text, LLM_SERVER, LLM_TEMPERATURE, ASR_MODEL, polish_text_file_path)
        print(f"润色后的文本已保存到：{polish_text_file_path}")
    else:
        polished_text = audio_text
        print("文本润色已跳过。")

    text_to_img_or_pdf(polished_text, title=audio_file.title, output_style=OUTPUT_STYLE, output_path=output_dir,
                       LLM_info=f'({LLM_SERVER}, 温度: {LLM_TEMPERATURE})', ASR_model=ASR_MODEL)

    if not DISABLE_LLM_SUMMARY:
        print("正在生成 Summary...")
        summary_text = summarize_text(txt=polished_text, api_server=SUMMARY_LLM_SERVER,
                                      temperature=SUMMARY_LLM_TEMPERATURE, max_tokens=SUMMARY_LLM_MAX_TOKENS,
                                      title=audio_file.title)
        with open(os.path.join(OUTPUT_DIR, "summary_text.md"), "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"文本摘要已保存到：{os.path.join(output_dir, 'summary_text.md')}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        main()
