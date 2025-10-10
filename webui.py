import shutil

import gradio as gr

from src.Timer import Timer
from src.bilibili_downloader import download_bilibili_audio, extract_audio_from_video, BiliVideoFile, \
    new_local_bili_file
from src.config import *
from src.core_process import (
    process_audio, upload_audio
)
from src.subtitle_generator import hard_encode_dot_srt_file, gen_timestamped_text_file


def zip_output_dir(output_dir: str) -> str:
    """
    压缩输出目录为ZIP文件
    """
    print(f"正在压缩输出目录：{output_dir}")
    zip_path = f"{output_dir}.zip"
    shutil.make_archive(base_name=output_dir, format="zip", root_dir=output_dir)
    print(f"压缩文件已保存到：{zip_path}")
    return zip_path


def upload_audio(audio_path, llm_api, temperature, max_tokens):
    if audio_path is None:
        return "请上传一个音频文件。", None, None, None, None, None
    audio_file = new_local_bili_file(audio_path)
    return process_audio(audio_file, llm_api, temperature, max_tokens)


def bilibili_video_download_process(video_url, llm_api, temperature, max_tokens):
    """
    处理B站视频链接，下载音频并提取文本
    """
    if not video_url.startswith("http"):
        return "请输入正确的B站链接。", None, None, None, None, None
    timer = Timer()
    timer.start()
    audio_file: BiliVideoFile = download_bilibili_audio(video_url, output_format='mp3', output_dir=DOWNLOAD_DIR)
    download_time = timer.stop()
    output_dir, extract_time, polish_time, zip_file = process_audio(
        audio_file, llm_api, temperature, max_tokens
    )
    return output_dir, extract_time + download_time, polish_time, zip_file


def process_multiple_urls(urls: str, llm_api=LLM_SERVER, temperature=LLM_TEMPERATURE,
                          max_tokens=LLM_MAX_TOKENS):
    url_list = urls.strip().split("\n")
    all_output_dirs = []
    total_extract_time = 0
    total_polish_time = 0
    for url in url_list:
        if url.startswith("http"):
            timer = Timer()
            timer.start()
            audio_file = download_bilibili_audio(url, output_format='mp3', output_dir=DOWNLOAD_DIR)
            download_time = timer.stop()
            output_dir, extract_time, polish_time, zip_file = process_audio(
                audio_file, llm_api, temperature, max_tokens
            )
            all_output_dirs.append(zip_file)
            total_extract_time += extract_time + download_time
            total_polish_time += polish_time
        else:
            return f"无效的URL: {url}", None, None, None, None, None
    return "\n".join(all_output_dirs), total_extract_time, total_polish_time, None, None, None


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


with gr.Blocks(title="音频识别与文本整理工具") as app:
    gr.Markdown("# 🎧 音频识别与文本整理系统")
    gr.Markdown("上传音频文件或输入B站视频链接，一键提取文本并生成图文版。")

    with gr.Tab("输入B站链接"):
        with gr.Row():
            bilibili_input = gr.Textbox(label="请输入B站视频链接")
        with gr.Row():
            llm_api_dropdown2 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
            temp_slider2 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
            token_slider2 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
        bilibili_button = gr.Button("下载并处理")
        bilibili_output = gr.Textbox(label="输出目录", interactive=False)
        bilibili_time = gr.Textbox(label="下载+识别+润色用时（秒）", interactive=False)

        with gr.Row():
            download_zip2 = gr.File(label="下载打包结果（ZIP）", interactive=False)

        bilibili_button.click(
            fn=bilibili_video_download_process,
            inputs=[bilibili_input, llm_api_dropdown2, temp_slider2, token_slider2],
            outputs=[bilibili_output, bilibili_time, bilibili_time, download_zip2]
        )

    with gr.Tab("批量处理B站链接"):
        with gr.Row():
            url_input = gr.Textbox(label="请输入B站视频链接，每个URL换行分隔")
        with gr.Row():
            llm_api_dropdown3 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
            temp_slider3 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
            token_slider3 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
        batch_button = gr.Button("批量下载并处理")
        batch_output = gr.Textbox(label="输出文件", interactive=False)
        batch_time = gr.Textbox(label="总下载+识别+润色用时（秒）", interactive=False)
        with gr.Row():
            download_zip_batch = gr.File(label="下载打包结果（ZIP）", interactive=False)

        batch_button.click(
            fn=process_multiple_urls,
            inputs=[url_input, llm_api_dropdown3, temp_slider3, token_slider3],
            outputs=[batch_output, batch_time, batch_time, download_zip_batch]
        )

    with gr.Tab("上传本地音频文件"):
        with gr.Row():
            audio_input = gr.File(label="选择本地音频文件（支持mp3/wav格式）")
        with gr.Row():
            llm_api_dropdown1 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
            temp_slider1 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
            token_slider1 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
        upload_button = gr.Button("开始处理")
        upload_output = gr.Textbox(label="输出目录", interactive=False)
        upload_time = gr.Textbox(label="识别+润色用时（秒）", interactive=False)

        with gr.Row():
            download_zip1 = gr.File(label="下载打包结果（ZIP）", interactive=False)

        upload_button.click(
            fn=upload_audio,
            inputs=[audio_input, llm_api_dropdown1, temp_slider1, token_slider1],
            outputs=[upload_output, upload_time, upload_time, download_zip1]
        )

    with gr.Tab("上传本地视频文件"):
        with gr.Row():
            video_input2 = gr.File(label="选择本地视频文件（支持mp4格式）")
        video_button = gr.Button("提取音频并处理")
        video_output = gr.Textbox(label="输出目录", interactive=False)
        video_time = gr.Textbox(label="提取+识别+润色用时（秒）", interactive=False)

        with gr.Row():
            download_zip_video = gr.File(label="下载打包结果（ZIP）", interactive=False)

        video_button.click(
            fn=lambda vf, api, temp, tokens: upload_audio(
                extract_audio_from_video(vf), api, temp, tokens
            ) if vf else ("请上传一个视频文件。", None, None, None),
            inputs=[video_input2, llm_api_dropdown1, temp_slider1, token_slider1],
            outputs=[video_output, video_time, video_time, download_zip_video]
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
    app.launch(server_name="localhost", inbrowser=True, server_port=WEB_SEVER_PORT)
