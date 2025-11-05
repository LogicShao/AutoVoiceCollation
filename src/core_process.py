import shutil
import uuid

from config import *
from src.Timer import Timer
from src.bilibili_downloader import download_bilibili_audio, extract_audio_from_video, BiliVideoFile, \
    new_local_bili_file
from src.extract_audio_text import extract_audio_text
from src.logger import get_logger
from src.subtitle_generator import hard_encode_dot_srt_file, gen_timestamped_text_file
from src.task_manager import get_task_manager, TaskCancelledException
from src.text_arrangement.polish_by_llm import polish_text
from src.text_arrangement.summary_by_llm import summarize_text
from src.text_arrangement.text_exporter import text_to_img_or_pdf

logger = get_logger(__name__)
task_manager = get_task_manager()


def zip_output_dir(output_dir: str) -> str:
    """
    压缩输出目录为ZIP文件
    """
    if not ZIP_OUTPUT_ENABLED:
        return None
    zip_path = f"{output_dir}.zip"
    shutil.make_archive(base_name=output_dir, format="zip", root_dir=output_dir)
    return zip_path


def process_audio(audio_file: BiliVideoFile, llm_api: str, temperature: float, max_tokens: int,
                  text_only: bool = False, task_id: str = None):
    """
    处理音频文件，提取文本并润色
    :param audio_file: 音频文件对象
    :param llm_api: LLM API服务
    :param temperature: 温度参数
    :param max_tokens: 最大token数
    :param text_only: 是否只返回纯文本结果（不生成PDF）
    :param task_id: 任务ID，用于终止控制
    :return: 输出目录, 提取时间, 润色时间, zip文件路径
    """
    # 如果没有提供 task_id，生成一个
    if task_id is None:
        task_id = str(uuid.uuid4())

    # 创建任务
    task_manager.create_task(task_id)

    try:
        # 输入验证
        if not os.path.exists(audio_file.path):
            raise FileNotFoundError(f"Audio file not found: {audio_file.path}")
        if not 0 <= temperature <= 2:
            raise ValueError(f"Temperature must be between 0 and 2, got {temperature}")
        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")
        if llm_api not in LLM_SERVER_SUPPORTED:
            raise ValueError(f"Unsupported LLM API: {llm_api}. Supported: {LLM_SERVER_SUPPORTED}")

        # 检查是否应该停止
        if task_manager.should_stop(task_id):
            raise TaskCancelledException(f"Task {task_id} was cancelled before starting")

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        timer = Timer()
        audio_file_name = os.path.basename(audio_file.path).split(".")[0]
        output_dir = os.path.join(OUTPUT_DIR, audio_file_name)
        if os.path.exists(output_dir):
            suffix_id = 1
            while os.path.exists(f"{output_dir}_{suffix_id}"):
                suffix_id += 1
            output_dir = f"{output_dir}_{suffix_id}"
        os.makedirs(output_dir)
        info_file_path = os.path.join(output_dir, "video_info.txt")
        audio_file.save_in_json(info_file_path)

        # 检查是否应该停止
        if task_manager.should_stop(task_id):
            raise TaskCancelledException(f"Task {task_id} was cancelled during setup")

        timer.start()
        audio_text = extract_audio_text(input_audio_path=audio_file.path, model_type=ASR_MODEL)
        text_file_path = os.path.join(output_dir, "audio_transcription.txt")
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(audio_text)
        extract_time = timer.stop()

        # 检查是否应该停止
        if task_manager.should_stop(task_id):
            raise TaskCancelledException(f"Task {task_id} was cancelled after ASR")

        if not DISABLE_LLM_POLISH:
            timer.start()
            polished_text = polish_text(audio_text, api_service=llm_api, split_len=round(max_tokens * 0.7),
                                        temperature=temperature, max_tokens=max_tokens, debug_flag=DEBUG_FLAG,
                                        async_flag=ASYNC_FLAG)
            polish_text_file_path = os.path.join(output_dir, "polish_text.txt")
            audio_file.save_in_text(polished_text, llm_api, temperature, ASR_MODEL, polish_text_file_path)
            polish_time = timer.stop()
        else:
            polished_text = audio_text
            polish_time = 0

        # 检查是否应该停止
        if task_manager.should_stop(task_id):
            raise TaskCancelledException(f"Task {task_id} was cancelled after polishing")

        # 如果只需要纯文本输出，保存为JSON并跳过PDF/图片生成
        if text_only:
            import json
            result_data = {
                "title": audio_file.title,
                "audio_file": audio_file.path,
                "asr_model": ASR_MODEL,
                "llm_api": llm_api,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "extract_time": extract_time,
                "polish_time": polish_time,
                "audio_text": audio_text,
                "polished_text": polished_text
            }
            json_file_path = os.path.join(output_dir, "result.json")
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Text-only result saved to {json_file_path}")
            logger.info('all done')
            # 返回文本内容而不是文件路径
            return result_data, extract_time, polish_time, None

        # 正常模式：生成PDF/图片和摘要
        text_to_img_or_pdf(polished_text, title=audio_file.title, output_style=OUTPUT_STYLE, output_path=output_dir,
                           LLM_info=f'({llm_api},温度:{temperature})', ASR_model=ASR_MODEL)

        # 检查是否应该停止
        if task_manager.should_stop(task_id):
            raise TaskCancelledException(f"Task {task_id} was cancelled after PDF generation")

        summary_text = summarize_text(txt=polished_text, api_server=SUMMARY_LLM_SERVER,
                                      temperature=SUMMARY_LLM_TEMPERATURE,
                                      max_tokens=SUMMARY_LLM_MAX_TOKENS, title=audio_file.title)
        md_file_path = os.path.join(output_dir, "summary_text.md")
        with open(md_file_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        logger.info(f"Summary text saved to {md_file_path}")
        zip_file = zip_output_dir(output_dir)
        logger.info('all done')
        return output_dir, extract_time, polish_time, zip_file

    except TaskCancelledException as e:
        logger.warning(f"Task cancelled: {e}")
        return f"任务已取消: {task_id}", 0, 0, None
    finally:
        # 清理任务
        task_manager.remove_task(task_id)


def process_multiple_urls(urls: str, llm_api=LLM_SERVER, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS,
                          text_only: bool = False, task_id: str = None):
    """
    批量处理B站视频链接
    :param urls: 多个URL，用换行符分隔
    :param llm_api: LLM API服务
    :param temperature: 温度参数
    :param max_tokens: 最大token数
    :param text_only: 是否只返回纯文本结果（不生成PDF）
    :param task_id: 任务ID，用于终止控制
    :return: 输出结果
    """
    # 如果没有提供 task_id，生成一个
    if task_id is None:
        task_id = str(uuid.uuid4())

    # 创建任务
    task_manager.create_task(task_id)

    try:
        # 输入验证
        if not urls or not urls.strip():
            raise ValueError("URLs cannot be empty")

        url_list = urls.strip().split("\n")
        all_output_dirs = []
        total_extract_time = 0
        total_polish_time = 0
        for url in url_list:
            url = url.strip()
            if not url:
                continue

            # 检查是否应该停止
            if task_manager.should_stop(task_id):
                raise TaskCancelledException(f"Batch task {task_id} was cancelled")

            if url.startswith("http"):
                timer = Timer()
                timer.start()
                audio_file = download_bilibili_audio(url, output_format='mp3', output_dir=DOWNLOAD_DIR)
                download_time = timer.stop()

                # 检查是否应该停止
                if task_manager.should_stop(task_id):
                    raise TaskCancelledException(f"Batch task {task_id} was cancelled")

                output_dir, extract_time, polish_time, zip_file = process_audio(
                    audio_file, llm_api, temperature, max_tokens, text_only, task_id
                )
                if ZIP_OUTPUT_ENABLED:
                    all_output_dirs.append(zip_file)
                else:
                    all_output_dirs.append(output_dir)
                total_extract_time += extract_time + download_time
                total_polish_time += polish_time
            else:
                raise ValueError(f"Invalid URL: {url}")
        return "\n".join(all_output_dirs), total_extract_time, total_polish_time, None, None, None

    except TaskCancelledException as e:
        logger.warning(f"Batch task cancelled: {e}")
        return f"批量任务已取消: {task_id}", 0, 0, None
    finally:
        # 清理任务
        task_manager.remove_task(task_id)


def process_subtitles(video_file: str):
    """
    生成视频字幕并硬编码到视频
    :param video_file: 视频文件路径
    :return: 字幕文件路径, 输出视频路径
    """
    if not video_file or not os.path.exists(video_file):
        raise FileNotFoundError(f"Video file not found: {video_file}")

    audio_file = extract_audio_from_video(video_file)
    srt_file = gen_timestamped_text_file(audio_file)
    output_file = hard_encode_dot_srt_file(video_file, srt_file)
    return srt_file, output_file


def upload_audio(audio_path, llm_api, temperature, max_tokens, text_only: bool = False, task_id: str = None):
    """
    上传并处理音频文件
    :param audio_path: 音频文件路径
    :param llm_api: LLM API服务
    :param temperature: 温度参数
    :param max_tokens: 最大token数
    :param text_only: 是否只返回纯文本结果（不生成PDF）
    :param task_id: 任务ID，用于终止控制
    :return: 处理结果
    """
    if audio_path is None:
        return "请上传一个音频文件。", None, None, None, None, None
    audio_file = new_local_bili_file(audio_path)
    return process_audio(audio_file, llm_api, temperature, max_tokens, text_only, task_id)


def bilibili_video_download_process(video_url, llm_api, temperature, max_tokens, text_only: bool = False,
                                    task_id: str = None):
    """
    下载并处理B站视频
    :param video_url: B站视频URL
    :param llm_api: LLM API服务
    :param temperature: 温度参数
    :param max_tokens: 最大token数
    :param text_only: 是否只返回纯文本结果（不生成PDF）
    :param task_id: 任务ID，用于终止控制
    :return: 处理结果
    """
    # 如果没有提供 task_id，生成一个
    if task_id is None:
        task_id = str(uuid.uuid4())

    # 创建任务
    task_manager.create_task(task_id)

    try:
        if not video_url or not video_url.startswith("http"):
            return "请输入正确的B站链接。", None, None, None, None, None

        # 检查是否应该停止
        if task_manager.should_stop(task_id):
            raise TaskCancelledException(f"Task {task_id} was cancelled before download")

        timer = Timer()
        timer.start()
        audio_file: BiliVideoFile = download_bilibili_audio(video_url, output_format='mp3', output_dir=DOWNLOAD_DIR)
        download_time = timer.stop()

        # 检查是否应该停止
        if task_manager.should_stop(task_id):
            raise TaskCancelledException(f"Task {task_id} was cancelled after download")

        output_dir, extract_time, polish_time, zip_file = process_audio(
            audio_file, llm_api, temperature, max_tokens, text_only, task_id
        )
        return output_dir, extract_time + download_time, polish_time, zip_file

    except TaskCancelledException as e:
        logger.warning(f"Task cancelled: {e}")
        return f"任务已取消: {task_id}", 0, 0, None
    finally:
        # 清理任务
        task_manager.remove_task(task_id)
