import shutil

import gradio as gr

from src.Timer import Timer
from src.config import *
from src.extract_audio_text import extract_audio_text
from src.get_timestamp import hard_encode_dot_srt_file, gen_timestamped_text_file
from src.get_video_or_audio import download_bilibili_audio, extract_audio_from_video
from src.output_file_manager import move_output_files
from src.text_arrangement.polish_by_llm import polish_text
from src.text_arrangement.summary_by_llm import summarize_text
from src.text_arrangement.text_exporter import text_to_img_or_pdf


def zip_output_dir(output_dir: str) -> str:
    """
    压缩输出目录为ZIP文件
    """
    print(f"正在压缩输出目录：{output_dir}")
    zip_path = f"{output_dir}.zip"
    shutil.make_archive(base_name=output_dir, format="zip", root_dir=output_dir)
    print(f"压缩文件已保存到：{zip_path}")
    return zip_path


def process_audio(audio_path: str, language: str, llm_api: str, temperature: float, max_tokens: int):
    """
    处理音频文件，提取文本并生成图文版
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    timer = Timer()
    audio_file_name = os.path.basename(audio_path).split(".")[0]

    # 提取文本
    timer.start()
    audio_text = extract_audio_text(audio_path, language=language)
    text_file_path = os.path.join(OUTPUT_DIR, "audio_transcription.txt")
    with open(text_file_path, "w", encoding="utf-8") as f:
        f.write(audio_text)
    extract_time = timer.stop()

    # 文本润色
    if not DISABLE_LLM_POLISH:
        timer.start()
        polished_text = polish_text(audio_text, api_service=llm_api, split_len=round(max_tokens * 0.7),
                                    temperature=temperature, max_tokens=max_tokens, debug_flag=DEBUG_FLAG,
                                    async_flag=ASYNC_FLAG)
        polish_text_file_path = os.path.join(OUTPUT_DIR, "polish_text.txt")
        with open(polish_text_file_path, "w", encoding="utf-8") as f:
            f.write(polished_text)
        polish_time = timer.stop()
    else:
        polished_text = audio_text
        polish_time = 0

    text_to_img_or_pdf(polished_text, title=audio_file_name, output_style=OUTPUT_STYLE, output_path=OUTPUT_DIR,
                       LLM_info='({},温度:{})'.format(llm_api, temperature))
    summary_text = summarize_text(txt=polished_text, api_server=llm_api, temperature=SUMMARY_LLM_TEMPERATURE,
                                  max_tokens=SUMMARY_LLM_MAX_TOKENS, title=audio_file_name)
    with open(os.path.join(OUTPUT_DIR, "summary_text.md"), "w", encoding="utf-8") as f:
        f.write(summary_text)
    output_dir = move_output_files(audio_file_name)
    zip_file = zip_output_dir(output_dir)
    return output_dir, extract_time, polish_time, zip_file


def upload_audio(audio_file, language, llm_api, temperature, max_tokens):
    if audio_file is None:
        return "请上传一个音频文件。", None, None, None
    return process_audio(audio_file, language, llm_api, temperature, max_tokens)


def bilibili_download(video_url, language, llm_api, temperature, max_tokens):
    if not video_url.startswith("http"):
        return "请输入正确的B站链接。", None, None, None
    timer = Timer()
    timer.start()
    audio_path = download_bilibili_audio(video_url, output_format='mp3', output_dir=DOWNLOAD_DIR)
    download_time = timer.stop()
    output_dir, extract_time, polish_time, zip_file = process_audio(
        audio_path, language, llm_api, temperature, max_tokens
    )
    return output_dir, extract_time + download_time, polish_time, zip_file


def process_multiple_urls(urls: str, language="auto", llm_api=LLM_SERVER, temperature=LLM_TEMPERATURE,
                          max_tokens=LLM_MAX_TOKENS):
    url_list = urls.strip().split("\n")
    all_output_dirs = []
    total_extract_time = 0
    total_polish_time = 0
    for url in url_list:
        if url.startswith("http"):
            timer = Timer()
            timer.start()
            audio_path = download_bilibili_audio(url, output_format='mp3', output_dir=DOWNLOAD_DIR)
            download_time = timer.stop()
            output_dir, extract_time, polish_time, zip_file = process_audio(
                audio_path, language, llm_api, temperature, max_tokens
            )
            all_output_dirs.append(zip_file)
            total_extract_time += extract_time + download_time
            total_polish_time += polish_time
        else:
            return f"无效的URL: {url}", None
    return "\n".join(all_output_dirs), total_extract_time, total_polish_time


def process_subtitles(video_file: str):
    """
    硬编码字幕到视频文件
    :param video_file: 视频文件路径
    :return: 输出视频路径
    """
    audio_file = extract_audio_from_video(video_file)
    srt_file = gen_timestamped_text_file(audio_file)
    output_file = hard_encode_dot_srt_file(video_file, srt_file)
    return srt_file, output_file


with gr.Blocks(title="音频识别与文本整理工具") as app:  # TODO: 改进UI
    gr.Markdown("# 🎧 音频识别与文本整理系统")
    gr.Markdown("上传音频文件或输入B站视频链接，一键提取文本并生成图文版。")

    LANGUAGES = ["auto", "zh", "en", "yue", "ja", "ko", "nospeech"]

    with gr.Tab("输入B站链接"):
        with gr.Row():
            bilibili_input = gr.Textbox(label="请输入B站视频链接")
            language_dropdown2 = gr.Dropdown(choices=LANGUAGES, value="auto", label="识别语言")
        # noinspection DuplicatedCode
        with gr.Row():
            llm_api_dropdown2 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
            temp_slider2 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
            token_slider2 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
        bilibili_button = gr.Button("下载并处理")
        bilibili_output = gr.Textbox(label="输出目录", interactive=False)
        bilibili_time = gr.Textbox(label="下载+识别+润色用时（秒）", interactive=False)
        download_zip2 = gr.File(label="下载打包结果（ZIP）", interactive=False)

        bilibili_button.click(
            fn=bilibili_download,
            inputs=[bilibili_input, language_dropdown2, llm_api_dropdown2, temp_slider2, token_slider2],
            outputs=[bilibili_output, bilibili_time, bilibili_time, download_zip2]
        )

    # New tab for processing multiple URLs
    with gr.Tab("批量处理B站链接"):
        with gr.Row():
            url_input = gr.Textbox(label="请输入B站视频链接，每个URL换行分隔")
            language_dropdown3 = gr.Dropdown(choices=LANGUAGES, value="auto", label="识别语言")
        with gr.Row():
            llm_api_dropdown3 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
            temp_slider3 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
            token_slider3 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
        batch_button = gr.Button("批量下载并处理")
        batch_output = gr.Textbox(label="输出文件", interactive=False)
        batch_time = gr.Textbox(label="总下载+识别+润色用时（秒）", interactive=False)
        download_zip_batch = gr.File(label="下载打包结果（ZIP）", interactive=False)

        batch_button.click(
            fn=process_multiple_urls,
            inputs=[url_input, language_dropdown3, llm_api_dropdown3, temp_slider3, token_slider3],
            outputs=[batch_output, batch_time, batch_time, download_zip_batch]
        )

    with gr.Tab("上传音频文件"):
        with gr.Row():
            audio_input = gr.File(label="选择本地音频文件（支持mp3/wav格式）")
            language_dropdown1 = gr.Dropdown(choices=LANGUAGES, value="auto", label="识别语言")
        # noinspection DuplicatedCode
        with gr.Row():
            llm_api_dropdown1 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
            temp_slider1 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
            token_slider1 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
        upload_button = gr.Button("开始处理")
        upload_output = gr.Textbox(label="输出目录", interactive=False)
        upload_time = gr.Textbox(label="识别+润色用时（秒）", interactive=False)
        download_zip1 = gr.File(label="下载打包结果（ZIP）", interactive=False)

        upload_button.click(
            fn=upload_audio,
            inputs=[audio_input, language_dropdown1, llm_api_dropdown1, temp_slider1, token_slider1],
            outputs=[upload_output, upload_time, upload_time, download_zip1]
        )

    with gr.Tab("自动添加字幕"):
        video_input = gr.File(label="选择视频文件（支持mp4格式）")
        subtitle_button = gr.Button("添加字幕并下载")
        dot_srt_file = gr.File(label="下载输出字幕文件（.srt）", interactive=False)
        subtitle_download = gr.File(label="下载带字幕的视频", interactive=False)

        subtitle_button.click(
            fn=process_subtitles,
            inputs=video_input,
            outputs=[dot_srt_file, subtitle_download]
        )

    gr.Markdown("---")
    gr.Markdown("处理完成后，可点击上方下载按钮获取完整输出。")

if __name__ == "__main__":
    app.launch(server_name="localhost", server_port=7860, inbrowser=True)
