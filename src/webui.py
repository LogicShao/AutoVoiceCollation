from .load_api_key import load_api_keys

load_api_keys()

import os

import gradio as gr

from .Timer import Timer
from .config import *
from .extract_audio_text import extract_audio_text
from .get_audio import download_bilibili_audio
from .scripts import copy_output_files
from .text_arrangement.polish_by_llm.polish_by_llm import polish_text
from .text_arrangement.text2img import text_to_image


def process_audio(audio_path: str):
    timer = Timer()
    audio_file_name = os.path.basename(audio_path).split(".")[0]

    # 提取文本
    timer.start()
    audio_text = extract_audio_text(audio_path, language="auto")
    text_file_path = os.path.join(OUTPUT_DIR, "audio_transcription.txt")
    with open(text_file_path, "w", encoding="utf-8") as f:
        f.write(audio_text)
    extract_time = timer.stop()

    # 文本润色
    if not DISABLE_LLM_POLISH:
        timer.start()
        polished_text = polish_text(audio_text, api_service=LLM_SERVER, temperature=LLM_TEMPERATURE,
                                    max_tokens=SPLIT_LIMIT, debug_flag=DEBUG_FLAG)
        polish_text_file_path = os.path.join(OUTPUT_DIR, "polish_text.txt")
        with open(polish_text_file_path, "w", encoding="utf-8") as f:
            f.write(polished_text)
        polish_time = timer.stop()
    else:
        polished_text = audio_text
        polish_time = 0

    # 生成图像
    text_to_image(polished_text, title=audio_file_name, output_style=OUTPUT_STYLE, output_path=OUTPUT_DIR)

    # 复制输出文件
    output_dir = copy_output_files(audio_file_name)

    return output_dir, extract_time, polish_time


def upload_audio(audio_file):
    if audio_file is None:
        return "请上传一个音频文件。", None, None
    return process_audio(audio_file)


def bilibili_download(video_url):
    if not video_url.startswith("http"):
        return "请输入正确的B站链接。", None, None
    timer = Timer()
    timer.start()
    audio_path = download_bilibili_audio(video_url, output_format='mp3', output_dir=DOWNLOAD_DIR)
    download_time = timer.stop()
    output_dir, extract_time, polish_time = process_audio(audio_path)
    return output_dir, extract_time + download_time, polish_time


with gr.Blocks(title="音频识别与文本整理工具") as demo:
    gr.Markdown("# 🎧 音频识别与文本整理系统")
    gr.Markdown("上传音频文件或输入B站视频链接，一键提取文本并生成图文版。")

    with gr.Tab("上传音频文件"):
        with gr.Row():
            audio_input = gr.File(label="选择本地音频文件（支持mp3/wav格式）")
            upload_button = gr.Button("开始处理")
        upload_output = gr.Textbox(label="输出目录", interactive=False)
        upload_time = gr.Textbox(label="识别+润色用时（秒）", interactive=False)

        upload_button.click(fn=upload_audio, inputs=[audio_input], outputs=[upload_output, upload_time, upload_time])

    with gr.Tab("输入B站链接"):
        with gr.Row():
            bilibili_input = gr.Textbox(label="请输入B站视频链接")
            bilibili_button = gr.Button("下载并处理")
        bilibili_output = gr.Textbox(label="输出目录", interactive=False)
        bilibili_time = gr.Textbox(label="下载+识别+润色用时（秒）", interactive=False)

        bilibili_button.click(fn=bilibili_download, inputs=[bilibili_input],
                              outputs=[bilibili_output, bilibili_time, bilibili_time])

    gr.Markdown("---")
    gr.Markdown("处理完成后，请到输出目录查看生成的文本和图片文件。")

if __name__ == "__main__":
    demo.launch(server_name="localhost", server_port=7860)
