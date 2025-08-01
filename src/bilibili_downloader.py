import os
import subprocess
import time

from yt_dlp import YoutubeDL


def download_bilibili_video(video_url, output_format='mp4', output_dir: str | None = None, retries: int = 3,
                            delay: float = 3.0) -> str:
    """
    带重试机制的 Bilibili 视频下载函数。

    :param video_url: Bilibili 视频的 URL
    :param output_format: 输出视频格式（如 'mp4', 'mkv' 等）
    :param output_dir: 输出目录（默认为当前目录）
    :param retries: 最大重试次数
    :param delay: 每次失败后等待的秒数
    :return: 下载成功后的视频文件路径
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"尝试第 {attempt} 次下载视频：{video_url}")
            return _download_bilibili_video_once(video_url, output_format, output_dir)
        except Exception as e:
            print(f"下载失败（第 {attempt} 次），错误信息：{e}")
            time.sleep(delay)
    raise RuntimeError("视频下载失败，已达最大重试次数。")


def _download_bilibili_video_once(video_url, output_format='mp4', output_dir: str | None = None) -> str:
    output_file_path = {'path': None}

    resolved_dir = os.getcwd() if output_dir is None else output_dir
    os.makedirs(resolved_dir, exist_ok=True)
    output_template = os.path.join(resolved_dir, '%(title)s.%(ext)s')

    # 获取视频信息（不下载，用于构建路径）
    with YoutubeDL({'quiet': True}) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)

    title = info_dict.get('title')
    filename = os.path.join(resolved_dir, f"{title}.{output_format}")

    if os.path.isfile(filename):
        print(f"已检测到本地缓存文件：{filename}，跳过下载。")
        return filename

    def hook(d):
        if d['status'] == 'finished' and 'filename' in d:
            output_file_path['path'] = d['filename']

    ydl_opts = {
        'format': 'bv+ba/best',
        'outtmpl': output_template,
        'progress_hooks': [hook],
        'noplaylist': True,
        'quiet': False
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    if output_file_path['path'] is not None:
        return output_file_path['path'].rsplit('.', 1)[0] + f'.{output_format}'

    if os.path.isfile(filename):
        print(f"文件已成功下载到：{filename}")
        return filename

    raise RuntimeError(f"未能捕获输出文件路径 {filename}，请检查下载流程")


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
            return _download_bilibili_audio_once(video_url, output_format, output_dir)
        except Exception as e:
            print(f"下载失败（第 {attempt} 次），错误信息：{e}")
            time.sleep(delay)
    raise RuntimeError("下载失败，已达最大重试次数。")


def _download_bilibili_audio_once(video_url, output_format='mp3', output_dir: str | None = None) -> str:
    output_file_path = {'path': None}

    resolved_dir = os.getcwd() if output_dir is None else output_dir
    os.makedirs(resolved_dir, exist_ok=True)
    output_template = os.path.join(resolved_dir, '%(title)s.%(ext)s')

    # 获取视频信息（不下载，用于构建文件名）
    with YoutubeDL({'quiet': True}) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)

    title = info_dict.get('title')
    filename = os.path.join(resolved_dir, f"{title}.{output_format}")

    if os.path.isfile(filename):
        print(f"音频文件已存在：{filename}，跳过下载。")
        return filename

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
        if os.path.isfile(filename):
            print(f"音频已成功下载：{filename}")
            return filename
        raise RuntimeError("未能捕获输出文件路径，请检查下载流程")

    return os.path.join(resolved_dir, f"{title}.{output_format}")


def extract_audio_from_video(video_path: str, output_format: str = 'mp3', output_dir: str | None = None) -> str:
    """
    从视频中提取音频并保存为指定格式。

    :param video_path: 视频文件路径
    :param output_format: 输出音频格式（如 'mp3', 'wav'）
    :param output_dir: 音频输出目录，默认为视频同目录
    :return: 提取后的音频文件路径
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"视频文件未找到：{video_path}")

    # 设置输出目录和文件名
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = output_dir or os.path.dirname(video_path)
    os.makedirs(output_dir, exist_ok=True)

    audio_path = os.path.join(output_dir, f"{base_name}.{output_format}")

    # 构造 ffmpeg 命令
    command = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # 不导出视频
        '-acodec', 'libmp3lame' if output_format == 'mp3' else 'pcm_s16le',
        '-y',  # 覆盖已存在文件
        audio_path
    ]

    print(f"开始提取音频：{audio_path}")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败：{result.stderr}")

    return audio_path
