"""
WebUI 历史检查功能集成示例

这个文件展示了如何在 webui.py 中集成处理历史检查功能。
使用方法：将下面的代码片段复制到 webui.py 的相应位置。
"""

import gradio as gr

from src.core_process_utils import check_bilibili_processed, record_bilibili_process, build_output_files_dict

# ========== 步骤 1: 在 webui.py 开头添加导入 ==========
# 在 webui.py 的导入部分添加以下代码：
"""
from src.core_process_utils import (
    check_bilibili_processed,
    record_bilibili_process,
    build_output_files_dict
)
"""


# ========== 步骤 2: 添加历史检查函数 ==========
def check_video_history(video_url):
    """
    检查视频是否已被处理过

    Args:
        video_url: B站视频URL

    Returns:
        tuple: (是否已处理, 提示信息, 历史记录)
    """
    if not video_url or not video_url.strip():
        return False, "", None

    record = check_bilibili_processed(video_url)
    if record:
        info = f"""
⚠️ 该视频已于 {record.last_processed} 处理过（共处理 {record.process_count} 次）

📁 上次输出目录: {record.output_dir}
🎯 使用配置:
  - ASR 模型: {record.config.get('asr_model', '未知')}
  - LLM 服务: {record.config.get('llm_api', '未知')}
  - Temperature: {record.config.get('temperature', '未知')}

💡 如果继续处理，将创建新的输出目录。
"""
        return True, info, record
    else:
        return False, "✅ 该视频尚未处理过", None


# ========== 步骤 3: 修改B站链接处理函数 ==========
def bilibili_process_wrapper_with_history(url, llm_api, temp, tokens, text_only, task_id):
    """
    带历史检查的B站视频处理包装函数

    这个函数替换原来的 bilibili_process_wrapper
    """
    # 先检查历史
    is_processed, history_info, record = check_video_history(url)

    if is_processed:
        # 如果已处理过，先显示历史信息
        yield f"{history_info}\n\n正在重新处理...", "", "", "", None
    else:
        yield "处理中...", "", "", "", None

    # 调用原来的处理逻辑
    from src.core_process import bilibili_video_download_process

    result = bilibili_video_download_process(url, llm_api, temp, tokens, text_only, task_id)
    result_data, extract_time, polish_time, zip_file = result

    # 处理返回数据
    if isinstance(result_data, dict):
        asr_text = result_data.get("audio_text", "")
        polished_text = result_data.get("polished_text", "")
        summary_text = result_data.get("summary_text", "") or "未生成摘要"
        output_dir = result_data.get("output_dir", "")

        # 记录处理历史
        if output_dir:
            try:
                config = {
                    "asr_model": ASR_MODEL,
                    "llm_api": llm_api,
                    "temperature": temp,
                    "max_tokens": tokens
                }
                outputs = build_output_files_dict(output_dir, text_only)
                record_bilibili_process(
                    video_url=url,
                    title=result_data.get("title", "Unknown"),
                    output_dir=output_dir,
                    config=config,
                    outputs=outputs
                )
            except Exception as e:
                logger.error(f"记录历史失败: {e}")
    else:
        # 错误情况
        asr_text = str(result_data)
        polished_text = ""
        summary_text = ""

    yield asr_text, polished_text, summary_text, extract_time, zip_file


# ========== 步骤 4: 在 Gradio UI 中添加历史检查按钮（可选）==========
def create_bilibili_tab_with_history():
    """
    创建带历史检查功能的B站链接输入Tab

    这个函数展示如何在 Gradio UI 中添加历史检查功能
    """
    with gr.Tab("输入B站链接（带历史检查）"):
        task_id_state = gr.State(value=None)

        with gr.Row():
            bilibili_input = gr.Textbox(label="请输入B站视频链接")

        # 历史检查按钮和显示区域
        with gr.Row():
            check_history_btn = gr.Button("🔍 检查处理历史", size="sm")

        history_info_box = gr.Textbox(
            label="历史记录信息",
            interactive=False,
            lines=6,
            visible=False
        )

        with gr.Row():
            llm_api_dropdown = gr.Dropdown(
                choices=LLM_SERVER_SUPPORTED,
                value=LLM_SERVER,
                label="选择LLM服务"
            )
            temp_slider = gr.Slider(0.0, 1.0, step=0.05, value=LLM_TEMPERATURE, label="Temperature")
            token_slider = gr.Slider(100, 8000, step=100, value=LLM_MAX_TOKENS, label="Max Tokens")
            text_only = gr.Checkbox(label="仅返回文本(JSON)", value=False)

        with gr.Row():
            process_button = gr.Button("下载并处理", variant="primary")
            stop_button = gr.Button("终止任务", variant="stop")

        # 文本展示区域
        with gr.Accordion("📝 处理结果文本", open=True):
            asr_text_output = gr.Textbox(label="ASR 识别文本", interactive=False, lines=8)
            polished_text_output = gr.Textbox(label="LLM 润色文本", interactive=False, lines=8)
            summary_text_output = gr.Textbox(label="文本摘要", interactive=False, lines=6)

        processing_time = gr.Textbox(label="下载+识别+润色用时（秒）", interactive=False)
        stop_status = gr.Textbox(label="终止状态", interactive=False)

        with gr.Row():
            download_zip = gr.File(label="下载打包结果（ZIP）", interactive=False)

        # 历史检查按钮事件
        def show_history(url):
            is_processed, info, _ = check_video_history(url)
            if is_processed:
                return gr.update(value=info, visible=True)
            else:
                return gr.update(value=info, visible=True)

        check_history_btn.click(
            fn=show_history,
            inputs=[bilibili_input],
            outputs=[history_info_box]
        )

        # 处理按钮事件
        from src.task_manager import get_task_manager
        task_manager = get_task_manager()

        def generate_task_id():
            task_id = str(uuid.uuid4())
            task_manager.create_task(task_id)
            return task_id

        process_button.click(
            fn=generate_task_id,
            inputs=[],
            outputs=[task_id_state]
        ).then(
            fn=bilibili_process_wrapper_with_history,
            inputs=[bilibili_input, llm_api_dropdown, temp_slider, token_slider, text_only, task_id_state],
            outputs=[asr_text_output, polished_text_output, summary_text_output, processing_time, download_zip]
        )

        def stop_task_fn(task_id):
            if task_id:
                task_manager.stop_task(task_id)
                return f"已请求终止任务: {task_id}"
            return "没有正在运行的任务"

        stop_button.click(
            fn=stop_task_fn,
            inputs=[task_id_state],
            outputs=[stop_status]
        )


# ========== 步骤 5: 在历史记录管理Tab（可选）==========
def create_history_management_tab():
    """
    创建历史记录管理Tab

    允许用户查看和管理处理历史
    """
    from src.process_history import get_history_manager
    history_manager = get_history_manager()

    with gr.Tab("📚 处理历史"):
        gr.Markdown("## 处理历史记录")
        gr.Markdown("查看和管理已处理的视频/音频文件记录")

        # 统计信息
        def get_stats():
            stats = history_manager.get_statistics()
            return f"""
### 📊 统计信息
- 总记录数: {stats['total_records']}
- B站视频: {stats['bilibili_videos']}
- 本地音频: {stats['local_audios']}
- 本地视频: {stats['local_videos']}
- 总处理次数: {stats['total_processes']}
"""

        stats_box = gr.Markdown(value=get_stats())
        refresh_btn = gr.Button("🔄 刷新统计")

        # 历史记录列表
        def format_records():
            records = history_manager.get_all_records()
            if not records:
                return "暂无处理记录"

            lines = []
            for i, record in enumerate(records[:20], 1):  # 只显示最近20条
                lines.append(f"""
**{i}. {record.title}**
- 类型: {record.record_type}
- 处理时间: {record.last_processed}
- 输出目录: {record.output_dir}
- 处理次数: {record.process_count}
- 配置: {record.config.get('asr_model', 'N/A')} + {record.config.get('llm_api', 'N/A')}
---
""")
            return "\n".join(lines)

        records_box = gr.Markdown(value=format_records(), label="历史记录列表")

        # 刷新按钮
        def refresh_all():
            return get_stats(), format_records()

        refresh_btn.click(
            fn=refresh_all,
            outputs=[stats_box, records_box]
        )

        # 清空历史（危险操作）
        with gr.Accordion("⚠️ 危险操作", open=False):
            gr.Markdown("**注意**: 清空历史记录不会删除实际输出文件，仅删除历史记录数据。")
            clear_confirm = gr.Textbox(
                label="输入 'CONFIRM' 以确认清空所有历史记录",
                placeholder="CONFIRM"
            )
            clear_btn = gr.Button("🗑️ 清空所有历史记录", variant="stop")
            clear_status = gr.Textbox(label="操作状态", interactive=False)

            def clear_history(confirm_text):
                if confirm_text == "CONFIRM":
                    history_manager.records.clear()
                    history_manager._save()
                    return "✅ 已清空所有历史记录"
                else:
                    return "❌ 确认文本不正确，操作已取消"

            clear_btn.click(
                fn=clear_history,
                inputs=[clear_confirm],
                outputs=[clear_status]
            )


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 示例：如何在现有 webui.py 中集成
    print("""

集成步骤总结：
================

1. 在 webui.py 开头添加导入：
   from src.core_process_utils import (
       check_bilibili_processed,
       record_bilibili_process,
       build_output_files_dict
   )

2. 复制 check_video_history 函数到 webui.py

3. 修改现有的 bilibili_process_wrapper 函数，添加历史检查和记录逻辑

4. （可选）添加历史检查按钮到 UI

5. （可选）添加历史记录管理Tab

详细代码请参考本文件中的示例函数。
    """)
