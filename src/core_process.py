import shutil

from src.Timer import Timer
from src.bilibili_downloader import download_bilibili_audio, extract_audio_from_video, BiliVideoFile, \
    new_local_bili_file
from src.config import *
from src.extract_audio_text import extract_audio_text
from src.subtitle_generator import hard_encode_dot_srt_file, gen_timestamped_text_file
from src.text_arrangement.polish_by_llm import polish_text
from src.text_arrangement.summary_by_llm import summarize_text
from src.text_arrangement.text_exporter import text_to_img_or_pdf


def zip_output_dir(output_dir: str) -> str:
    """
    压缩输出目录为ZIP文件
    """
    if not ZIP_OUTPUT_ENABLED:
        return None
    zip_path = f"{output_dir}.zip"
    shutil.make_archive(base_name=output_dir, format="zip", root_dir=output_dir)
    return zip_path


def process_audio(audio_file: BiliVideoFile, llm_api: str, temperature: float, max_tokens: int):
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
    timer.start()
    audio_text = extract_audio_text(input_audio_path=audio_file.path, model_type=ASR_MODEL)
    text_file_path = os.path.join(output_dir, "audio_transcription.txt")
    with open(text_file_path, "w", encoding="utf-8") as f:
        f.write(audio_text)
    extract_time = timer.stop()
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
    text_to_img_or_pdf(polished_text, title=audio_file.title, output_style=OUTPUT_STYLE, output_path=output_dir,
                       LLM_info=f'({llm_api},温度:{temperature})', ASR_model=ASR_MODEL)
    summary_text = summarize_text(txt=polished_text, api_server=SUMMARY_LLM_SERVER, temperature=SUMMARY_LLM_TEMPERATURE,
                                  max_tokens=SUMMARY_LLM_MAX_TOKENS, title=audio_file.title)
    md_file_path = os.path.join(output_dir, "summary_text.md")
    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    zip_file = zip_output_dir(output_dir)
    return output_dir, extract_time, polish_time, zip_file


def process_multiple_urls(urls: str, llm_api=LLM_SERVER, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS):
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
            if ZIP_OUTPUT_ENABLED:
                all_output_dirs.append(zip_file)
            else:
                all_output_dirs.append(output_dir)
            total_extract_time += extract_time + download_time
            total_polish_time += polish_time
        else:
            return f"无效的URL: {url}", None, None, None, None, None
    if ZIP_OUTPUT_ENABLED:
        return "\n".join(all_output_dirs), total_extract_time, total_polish_time, None, None, None
    else:
        return "\n".join(all_output_dirs), total_extract_time, total_polish_time, None, None, None


def process_subtitles(video_file: str):
    audio_file = extract_audio_from_video(video_file)
    srt_file = gen_timestamped_text_file(audio_file)
    output_file = hard_encode_dot_srt_file(video_file, srt_file)
    return srt_file, output_file


def upload_audio(audio_path, llm_api, temperature, max_tokens):
    if audio_path is None:
        return "请上传一个音频文件。", None, None, None, None, None
    audio_file = new_local_bili_file(audio_path)
    return process_audio(audio_file, llm_api, temperature, max_tokens)


def bilibili_video_download_process(video_url, llm_api, temperature, max_tokens):
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
