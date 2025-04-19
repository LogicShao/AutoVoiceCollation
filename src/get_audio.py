import os

import yt_dlp


def download_bilibili_audio(video_url, output_format='mp3', output_dir: str | None = None) -> str:
    """
    下载 Bilibili 视频的音频部分，并转换为指定格式。
    :param video_url: Bilibili 视频的 URL
    :param output_format: 输出音频格式（如 'mp3', 'wav' 等）
    :param output_dir: 输出目录，如果为 None，则使用默认目录
    :return: 下载的音频文件路径
    """
    output_file_path = {'path': None}  # 用于接收最终路径

    # 设置输出模板
    if output_dir is None:
        output_template = '%(title)s.%(ext)s'
    else:
        os.makedirs(output_dir, exist_ok=True)
        output_template = os.path.join(output_dir, '%(title)s.%(ext)s')

    # Hook 用于捕捉最终文件路径
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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    return output_file_path['path'].replace('m4a', output_format)
