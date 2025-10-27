import pathlib
import sys

import gradio as gr

from config import *
from src.bilibili_downloader import extract_audio_from_video
from src.core_process import (
    upload_audio, bilibili_video_download_process,
    process_multiple_urls, process_subtitles
)


# 配置管理函数
def load_env_config():
    """从.env文件加载配置"""
    env_path = pathlib.Path(__file__).resolve().parent / ".env"
    config = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config


def save_env_config(config_dict):
    """保存配置到.env文件"""
    env_path = pathlib.Path(__file__).resolve().parent / ".env"
    env_example_path = pathlib.Path(__file__).resolve().parent / ".env.example"

    # 读取示例文件以保留注释和结构
    lines = []
    if env_example_path.exists():
        with open(env_example_path, 'r', encoding='utf-8') as f:
            written_keys = set()
            for line in f:
                line_stripped = line.strip()
                # 如果是配置行，更新值
                if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                    key = line_stripped.split('=', 1)[0].strip()
                    if key in config_dict:
                        # 保留原始缩进
                        indent = len(line) - len(line.lstrip())
                        lines.append(' ' * indent + f"{key}={config_dict[key]}\n")
                        written_keys.add(key)
                    else:
                        lines.append(line)
                else:
                    lines.append(line)

            # 将示例中没有但 config_dict 有的键追加到末尾，保证新键被持久化
            for key, value in config_dict.items():
                if key not in written_keys:
                    lines.append(f"{key}={value}\n")
    else:
        # 如果没有示例文件，直接写入配置
        for key, value in config_dict.items():
            lines.append(f"{key}={value}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    return "配置已保存！需要重启应用以使配置生效。"


def update_config(
        # API Keys
        deepseek_key, gemini_key, dashscope_key, cerebras_key,
        # 目录
        output_dir, download_dir, temp_dir, model_dir, log_dir,
        # 日志
        log_level, log_file, log_console, log_colored, third_party_log_level,
        # ASR & 输出
        asr_model, output_style, zip_enabled,
        # UI 默认
        text_only_default,
        # LLM
        llm_server, llm_temp, llm_tokens, llm_top_p, llm_top_k, split_limit, async_flag,
        # 摘要
        summary_server, summary_temp, summary_tokens,
        # 功能开关
        disable_polish, disable_summary, local_llm, debug_flag,
        # Web
        web_port
):
    """更新配置"""
    config = {
        "DEEPSEEK_API_KEY": deepseek_key,
        "GEMINI_API_KEY": gemini_key,
        "DASHSCOPE_API_KEY": dashscope_key,
        "CEREBRAS_API_KEY": cerebras_key,
        "OUTPUT_DIR": output_dir,
        "DOWNLOAD_DIR": download_dir,
        "TEMP_DIR": temp_dir,
        "MODEL_DIR": model_dir,
        "LOG_DIR": log_dir,
        "LOG_LEVEL": log_level,
        "LOG_FILE": log_file,
        "LOG_CONSOLE_OUTPUT": str(log_console).lower(),
        "LOG_COLORED_OUTPUT": str(log_colored).lower(),
        "THIRD_PARTY_LOG_LEVEL": third_party_log_level,
        "ASR_MODEL": asr_model,
        "OUTPUT_STYLE": output_style,
        "ZIP_OUTPUT_ENABLED": str(zip_enabled).lower(),
        "TEXT_ONLY_DEFAULT": str(text_only_default).lower(),
        "LLM_SERVER": llm_server,
        "LLM_TEMPERATURE": str(llm_temp),
        "LLM_MAX_TOKENS": str(llm_tokens),
        "LLM_TOP_P": str(llm_top_p),
        "LLM_TOP_K": str(llm_top_k),
        "SPLIT_LIMIT": str(split_limit),
        "ASYNC_FLAG": str(async_flag).lower(),
        "SUMMARY_LLM_SERVER": summary_server,
        "SUMMARY_LLM_TEMPERATURE": str(summary_temp),
        "SUMMARY_LLM_MAX_TOKENS": str(summary_tokens),
        "DISABLE_LLM_POLISH": str(disable_polish).lower(),
        "DISABLE_LLM_SUMMARY": str(disable_summary).lower(),
        "LOCAL_LLM_ENABLED": str(local_llm).lower(),
        "DEBUG_FLAG": str(debug_flag).lower(),
        "WEB_SERVER_PORT": str(web_port) if web_port else "",
    }
    return save_env_config(config)


def create_app():
    with gr.Blocks(title="音频识别与文本整理工具") as app:
        gr.Markdown("# 🎧 音频识别与文本整理系统")
        gr.Markdown("上传音频文件或输入B站视频链接，一键提取文本并生成图文版。")
        # 预先加载 .env 配置，用于设置各 Tab 默认值（例如 TEXT_ONLY_DEFAULT）
        env_config = load_env_config()

        with gr.Tab("输入B站链接"):
            with gr.Row():
                bilibili_input = gr.Textbox(label="请输入B站视频链接")
            with gr.Row():
                llm_api_dropdown2 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
                temp_slider2 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
                token_slider2 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
                # 新增：仅返回纯文本(JSON)开关
                text_only2 = gr.Checkbox(label="仅返回文本(JSON)",
                                         value=env_config.get("TEXT_ONLY_DEFAULT", "false").lower() == "true")
            bilibili_button = gr.Button("下载并处理")
            bilibili_output = gr.Textbox(label="输出目录", interactive=False)
            bilibili_time = gr.Textbox(label="下载+识别+润色用时（秒）", interactive=False)

            with gr.Row():
                download_zip2 = gr.File(label="下载打包结果（ZIP）", interactive=False)

            bilibili_button.click(
                fn=bilibili_video_download_process,
                inputs=[bilibili_input, llm_api_dropdown2, temp_slider2, token_slider2, text_only2],
                outputs=[bilibili_output, bilibili_time, bilibili_time, download_zip2]
            )

        with gr.Tab("批量处理B站链接"):
            with gr.Row():
                url_input = gr.Textbox(label="请输入B站视频链接，每个URL换行分隔")
            with gr.Row():
                llm_api_dropdown3 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
                temp_slider3 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
                token_slider3 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
                # 新增：仅返回纯文本(JSON)开关
                text_only3 = gr.Checkbox(label="仅返回文本(JSON)",
                                         value=env_config.get("TEXT_ONLY_DEFAULT", "false").lower() == "true")
            batch_button = gr.Button("批量下载并处理")
            batch_output = gr.Textbox(label="输出文件", interactive=False)
            batch_time = gr.Textbox(label="总下载+识别+润色用时（秒）", interactive=False)
            with gr.Row():
                download_zip_batch = gr.File(label="下载打包结果（ZIP）", interactive=False)

            batch_button.click(
                fn=process_multiple_urls,
                inputs=[url_input, llm_api_dropdown3, temp_slider3, token_slider3, text_only3],
                outputs=[batch_output, batch_time, batch_time, download_zip_batch]
            )

        with gr.Tab("上传本地音频文件"):
            with gr.Row():
                audio_input = gr.File(label="选择本地音频文件（支持mp3/wav格式）")
            with gr.Row():
                llm_api_dropdown1 = gr.Dropdown(choices=LLM_SERVER_SUPPORTED, value=LLM_SERVER, label="选择LLM服务")
                temp_slider1 = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
                token_slider1 = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
                # 新增：仅返回纯文本(JSON)开关
                text_only1 = gr.Checkbox(label="仅返回文本(JSON)",
                                         value=env_config.get("TEXT_ONLY_DEFAULT", "false").lower() == "true")
            upload_button = gr.Button("开始处理")
            upload_output = gr.Textbox(label="输出目录", interactive=False)
            upload_time = gr.Textbox(label="识别+润色用时（秒）", interactive=False)

            with gr.Row():
                download_zip1 = gr.File(label="下载打包结果（ZIP）", interactive=False)

            upload_button.click(
                fn=upload_audio,
                inputs=[audio_input, llm_api_dropdown1, temp_slider1, token_slider1, text_only1],
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
                fn=lambda vf, api, temp, tokens, text_only: upload_audio(
                    extract_audio_from_video(vf), api, temp, tokens, text_only
                ) if vf else ("请上传一个视频文件。", None, None, None),
                inputs=[video_input2, llm_api_dropdown1, temp_slider1, token_slider1, text_only1],
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

        with gr.Tab("系统配置"):
            gr.Markdown("## 配置管理")
            gr.Markdown("在这里修改系统配置，保存后需要重启应用才能生效。")

            # 加载当前配置
            # env_config = load_env_config()

            with gr.Accordion("API Keys", open=True):
                deepseek_key = gr.Textbox(
                    label="DeepSeek API Key",
                    value=env_config.get("DEEPSEEK_API_KEY", ""),
                    type="password"
                )
                gemini_key = gr.Textbox(
                    label="Gemini API Key",
                    value=env_config.get("GEMINI_API_KEY", ""),
                    type="password"
                )
                dashscope_key = gr.Textbox(
                    label="DashScope API Key (通义千问)",
                    value=env_config.get("DASHSCOPE_API_KEY", ""),
                    type="password"
                )
                cerebras_key = gr.Textbox(
                    label="Cerebras API Key",
                    value=env_config.get("CEREBRAS_API_KEY", ""),
                    type="password"
                )

            with gr.Accordion("目录配置", open=False):
                output_dir = gr.Textbox(
                    label="输出目录",
                    value=env_config.get("OUTPUT_DIR", "./out")
                )
                download_dir = gr.Textbox(
                    label="下载目录",
                    value=env_config.get("DOWNLOAD_DIR", "./download")
                )
                temp_dir = gr.Textbox(
                    label="临时目录",
                    value=env_config.get("TEMP_DIR", "./temp")
                )
                model_dir = gr.Textbox(
                    label="模型目录（留空使用默认）",
                    value=env_config.get("MODEL_DIR", "")
                )
                log_dir = gr.Textbox(
                    label="日志目录",
                    value=env_config.get("LOG_DIR", "./logs")
                )

            with gr.Accordion("日志配置", open=False):
                log_level = gr.Dropdown(
                    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    label="日志级别",
                    value=env_config.get("LOG_LEVEL", "INFO")
                )
                log_file = gr.Textbox(
                    label="日志文件路径",
                    value=env_config.get("LOG_FILE", "./logs/AutoVoiceCollation.log")
                )
                log_console = gr.Checkbox(
                    label="输出到控制台",
                    value=env_config.get("LOG_CONSOLE_OUTPUT", "true").lower() == "true"
                )
                log_colored = gr.Checkbox(
                    label="彩色输出",
                    value=env_config.get("LOG_COLORED_OUTPUT", "true").lower() == "true"
                )
                third_party_log_level = gr.Dropdown(
                    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    label="第三方库日志级别",
                    value=env_config.get("THIRD_PARTY_LOG_LEVEL", "ERROR")
                )

            with gr.Accordion("ASR 和输出配置", open=False):
                asr_model = gr.Dropdown(
                    choices=["paraformer", "sense_voice"],
                    label="ASR 模型",
                    value=env_config.get("ASR_MODEL", "paraformer")
                )
                output_style = gr.Dropdown(
                    choices=["pdf_with_img", "img_only", "text_only", "pdf_only"],
                    label="输出样式",
                    value=env_config.get("OUTPUT_STYLE", "pdf_only")
                )
                zip_enabled = gr.Checkbox(
                    label="启用 ZIP 压缩输出",
                    value=env_config.get("ZIP_OUTPUT_ENABLED", "false").lower() == "true"
                )
                # 新增：记住 Web UI 中 text_only 的默认值
                text_only_default = gr.Checkbox(
                    label="默认仅返回文本(JSON)",
                    value=env_config.get("TEXT_ONLY_DEFAULT", "false").lower() == "true"
                )

            with gr.Accordion("LLM 配置", open=False):
                llm_server = gr.Dropdown(
                    choices=LLM_SERVER_SUPPORTED,
                    label="LLM 服务",
                    value=env_config.get("LLM_SERVER", "Cerebras:Qwen-3-235B-Instruct")
                )
                llm_temp = gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    step=0.05,
                    label="Temperature",
                    value=float(env_config.get("LLM_TEMPERATURE", "0.1"))
                )
                llm_tokens = gr.Slider(
                    minimum=100,
                    maximum=8000,
                    step=100,
                    label="Max Tokens",
                    value=int(env_config.get("LLM_MAX_TOKENS", "6000"))
                )
                llm_top_p = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    step=0.01,
                    label="Top P",
                    value=float(env_config.get("LLM_TOP_P", "0.95"))
                )
                llm_top_k = gr.Slider(
                    minimum=0,
                    maximum=100,
                    step=1,
                    label="Top K",
                    value=int(env_config.get("LLM_TOP_K", "64"))
                )
                split_limit = gr.Slider(
                    minimum=100,
                    maximum=5000,
                    step=100,
                    label="文本分段长度",
                    value=int(env_config.get("SPLIT_LIMIT", "1000"))
                )
                async_flag = gr.Checkbox(
                    label="启用异步处理",
                    value=env_config.get("ASYNC_FLAG", "true").lower() == "true"
                )

            with gr.Accordion("摘要生成配置", open=False):
                summary_server = gr.Dropdown(
                    choices=LLM_SERVER_SUPPORTED,
                    label="摘要 LLM 服务",
                    value=env_config.get("SUMMARY_LLM_SERVER", "Cerebras:Qwen-3-235B-Thinking")
                )
                summary_temp = gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    step=0.05,
                    label="摘要 Temperature",
                    value=float(env_config.get("SUMMARY_LLM_TEMPERATURE", "1.0"))
                )
                summary_tokens = gr.Slider(
                    minimum=100,
                    maximum=16000,
                    step=100,
                    label="摘要 Max Tokens",
                    value=int(env_config.get("SUMMARY_LLM_MAX_TOKENS", "8192"))
                )

            with gr.Accordion("功能开关", open=False):
                disable_polish = gr.Checkbox(
                    label="禁用 LLM 润色",
                    value=env_config.get("DISABLE_LLM_POLISH", "false").lower() == "true"
                )
                disable_summary = gr.Checkbox(
                    label="禁用 LLM 摘要",
                    value=env_config.get("DISABLE_LLM_SUMMARY", "false").lower() == "true"
                )
                local_llm = gr.Checkbox(
                    label="启用本地 LLM",
                    value=env_config.get("LOCAL_LLM_ENABLED", "false").lower() == "true"
                )
                debug_flag = gr.Checkbox(
                    label="调试模式",
                    value=env_config.get("DEBUG_FLAG", "false").lower() == "true"
                )

            with gr.Accordion("Web 服务器配置", open=False):
                web_port = gr.Number(
                    label="Web 服务器端口（留空为自动）",
                    value=int(env_config.get("WEB_SERVER_PORT", "0")) if env_config.get("WEB_SERVER_PORT",
                                                                                        "") else None,
                    precision=0
                )

            # 保存按钮和状态显示
            save_button = gr.Button("保存配置", variant="primary", size="lg")
            save_status = gr.Textbox(label="保存状态", interactive=False)

            # 绑定保存事件
            save_button.click(
                fn=update_config,
                inputs=[
                    deepseek_key, gemini_key, dashscope_key, cerebras_key,
                    output_dir, download_dir, temp_dir, model_dir, log_dir,
                    log_level, log_file, log_console, log_colored, third_party_log_level,
                    asr_model, output_style, zip_enabled, text_only_default,
                    llm_server, llm_temp, llm_tokens, llm_top_p, llm_top_k, split_limit, async_flag,
                    summary_server, summary_temp, summary_tokens,
                    disable_polish, disable_summary, local_llm, debug_flag,
                    web_port
                ],
                outputs=[save_status]
            )

    return app


def launch_ui(server_name: str = "0.0.0.0", server_port: int | None = None, share: bool = False):
    app = create_app()
    # 优先使用传入参数，其次使用配置中的 WEB_SERVER_PORT（如果有），否则让 gradio 自动选择
    port = server_port or (
        int(WEB_SERVER_PORT) if (globals().get('WEB_SERVER_PORT') and str(WEB_SERVER_PORT).strip()) else None)
    should_launch_browser = '--from-electron' not in sys.argv
    app.launch(server_name=server_name, server_port=port, share=share, inbrowser=should_launch_browser)


if __name__ == "__main__":
    launch_ui()
