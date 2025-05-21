import os
import time

from yt_dlp import YoutubeDL


def download_bilibili_audio(video_url, output_format='mp3', output_dir: str | None = None, retries: int = 3,
                            delay: float = 3.0) -> str:
    """
    带重试机制的 Bilibili 音频下载函数。

    :param video_url: Bilibili 视频的 URL
    :param output_format: 输出音频格式（如 'mp3', 'wav' 等）
    :param output_dir: 输出目录（默认为当前目录）
    :param retries: 最大重试次数
    :param delay: 每次失败后等待的秒数
    :return: 下载成功后的音频文件路径
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"尝试第 {attempt} 次下载：{video_url}")
            return _download_once(video_url, output_format, output_dir)
        except Exception as e:
            print(f"下载失败（第 {attempt} 次），错误信息：{e}")
            time.sleep(delay)
    raise RuntimeError("下载失败，已达最大重试次数。")


def _download_once(video_url, output_format='mp3', output_dir: str | None = None) -> str:
    output_file_path = {'path': None}

    # 设置输出模板
    if output_dir is None:
        output_template = '%(title)s.%(ext)s'
    else:
        os.makedirs(output_dir, exist_ok=True)
        output_template = os.path.join(output_dir, '%(title)s.%(ext)s')

    # Hook 捕获路径
    def hook(d):
        if d['status'] == 'finished' and 'filename' in d:
            output_file_path['path'] = d['filename']

    ydl_opts = {
        'format': 'ba',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': output_format,
            'preferredquality': '192',
        }],
        'progress_hooks': [hook],
        'noplaylist': True,
        'quiet': False
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    if output_file_path['path'] is None:
        raise RuntimeError("未能捕获输出文件路径，请检查下载流程")

    return output_file_path['path'].replace('m4a', output_format)
