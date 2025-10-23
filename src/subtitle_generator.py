import difflib
import os
import re
import subprocess
import sys
from datetime import timedelta
from typing import List, Dict

import jieba
import soundfile as sf
import torch
import torchaudio

from src.SenseVoiceSmall.model import SenseVoiceSmall
from src.extract_audio_text import get_paraformer_model
from src.logger import get_logger
from src.text_arrangement.query_llm import query_llm, LLMQueryParams
from src.text_arrangement.split_text import clean_asr_text, smart_split

logger = get_logger(__name__)


def slice_audio(audio_path, batch_size_s, sample_rate=16000):
    audio, sr = torchaudio.load(audio_path)
    if sr != sample_rate:
        audio = torchaudio.functional.resample(audio, sr, sample_rate)

    total_samples = audio.shape[1]
    samples_per_slice = int(batch_size_s * sample_rate)

    slices = []
    for i in range(0, total_samples, samples_per_slice):
        start = i
        end = min(i + samples_per_slice, total_samples)
        slice_audio = audio[:, start:end]
        slices.append((slice_audio, start / sample_rate, end / sample_rate))  # 秒级时间戳

    logger.debug(f"Total slices: {len(slices)}")
    return slices


def split_by_pause_and_semantics(char_time_list, pause_threshold=0.6, max_chars=15) -> List[Dict]:
    """
    结合语音停顿和语义边界进行字幕切分
    """
    segments = []
    current = []
    current_text = ""
    current_start = char_time_list[0][1]

    for i in range(len(char_time_list)):
        char, start, end = char_time_list[i]
        if not current:
            current_start = start
        current.append((char, start, end))
        current_text += char

        # 判断是否满足分段条件
        pause = (char_time_list[i + 1][1] - end) if i + 1 < len(char_time_list) else 0
        over_length = len(current_text) >= max_chars
        is_pause = pause > pause_threshold

        if over_length or is_pause:
            # NLP 分词判断语义边界是否合理
            words_list = list(jieba.cut(current_text))
            if len(words_list) <= 1 and not is_pause:
                continue  # 不太可能是语义边界，跳过

            segments.append({
                "text": current_text,
                "start_time": current_start,
                "end_time": end
            })
            current = []
            current_text = ""

    # 剩余部分
    if current:
        segments.append({
            "text": current_text,
            "start_time": current_start,
            "end_time": current[-1][2]
        })

    return segments


def levenshtein_distance(s1: str, s2: str) -> int:
    len_s1, len_s2 = len(s1), len(s2)
    dp = [[0] * (len_s2 + 1) for _ in range(len_s1 + 1)]
    for i in range(len_s1 + 1):
        dp[i][0] = i
    for j in range(len_s2 + 1):
        dp[0][j] = j
    for i in range(1, len_s1 + 1):
        for j in range(1, len_s2 + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + 1
                )
    return dp[len_s1][len_s2]


def is_likely_string(processed_txt: str, original_txt: str, max_error: int) -> bool:
    return levenshtein_distance(processed_txt, original_txt) <= max_error


def fix_split_list(split_list: List[str], original_text: str, max_error: int = 5) -> List[str]:  # TODO: 改善此处的逻辑
    """
    如果 processed_txt 与 original_text 足够接近，基于 split_list 中每段内容在原文中匹配修复；
    否则放弃此切分，返回空列表。
    """
    processed_txt = ''.join(split_list)
    if not is_likely_string(processed_txt, original_text, max_error):
        return []  # 不接受这个分割结果

    repaired = []
    cursor = 0  # 原文中当前搜索起点

    for seg in split_list:
        # 在原文当前位置之后搜索最匹配的片段
        search_window = original_text[cursor:]
        matcher = difflib.SequenceMatcher(None, seg, search_window)
        match = matcher.find_longest_match(0, len(seg), 0, len(search_window))

        if match.size == 0:
            return []  # 匹配失败，返回空列表

        start = cursor + match.b  # 在原文中的起始位置
        end = start + match.size

        # 为了处理替换、错字，尽量扩展原始文本范围以包含完整内容
        # 扩展长度以 seg 长度为准（避免切得太短）
        end = max(end, start + len(seg))
        end = min(end, len(original_text))  # 不越界

        repaired.append(original_text[start:end])
        cursor = end  # 更新游标位置

    return repaired


def split_by_llm(timestamp_data, max_char_per_seg=16, split_len=600, max_tokens=1000, api_server="gemini",
                 temperature=0.0, top_p=0.95, top_k=1, llm_retry=3) -> List[Dict]:
    """
    使用 LLM 对时间戳数据进行分段
    :param timestamp_data: 包含时间戳的字典，格式为 {"text": str, "timestamp": [[char, start_time, end_time], ...]}
    :param max_char_per_seg: 每段的最大字符数
    :param split_len: 每段的最大长度（字符数），如果处理的文本过多需要对于文本进行分割
    :param max_tokens: LLM 的最大令牌数
    :param api_server: 使用的 LLM API 服务器（默认 "gemini"）
    :param temperature: LLM 的温度参数
    :param llm_retry: LLM 查询失败时的重试次数
    :param top_p: LLM 的 top_p 参数
    :param top_k: LLM 的 top_k 参数
    :return: 分段后的时间戳数据列表
    例如：
    [
        {"text": "第一段文本", "start_time": 0.0, "end_time": 5.0},
        {"text": "第二段文本", "start_time": 5.0, "end_time": 10.0}
    ]
    """
    if not timestamp_data["timestamp"]:
        return []

    assert (split_len <= max_tokens), "分段长度不能超过max_tokens，这可能导致部分文字丢失。请调整参数。"

    full_text = timestamp_data["text"]
    full_text_without_spaces = full_text.replace(" ", "")
    char_time_list = timestamp_data["timestamp"]
    segments = []

    # 将全文切片（如果太长）
    text_chunks = smart_split(full_text, split_len=split_len)

    # 时间游标（用于和 timestamp 匹配）
    time_cursor = 0

    for chunk in text_chunks:
        system_instruction = (
            "你是一个字幕切分助手，请根据自然语言的语义逻辑，将以下文本切分为适合显示在屏幕上的多行字幕。"
            f"每行字幕最长不要超过{max_char_per_seg}个字符。请在每个切分点用英文符号“|”表示，"
            "不要换行，不要添加其他文字、不要缺少文字、也不要替换文字。"
        )

        llm_input = LLMQueryParams(
            content=chunk,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
            api_server=api_server,
            top_p=top_p,
            top_k=top_k
        )

        chunk_without_spaces = chunk.replace(" ", "").replace("\n", "")

        for try_count in range(llm_retry):
            logger.info(f"正在查询 LLM，尝试次数：{try_count + 1}/{llm_retry}，内容长度：{len(chunk)}")

            response = query_llm(llm_input)
            response_text = response.replace(" ", "").replace("\n", "")
            split_parts = response_text.split("|")
            response_full_text = ''.join(split_parts)
            logger.debug(response_full_text)
            logger.debug(chunk_without_spaces)

            if is_likely_string(response_full_text, chunk_without_spaces, max_error=2):
                logger.info(f"LLM 查询成功。")

                fixed_split_list = fix_split_list(split_parts, chunk_without_spaces)
                for part in fixed_split_list:
                    sub_chars = []
                    match_part = ""

                    while match_part != part:
                        sub_chars.append(char_time_list[time_cursor])
                        match_part += char_time_list[time_cursor][0]
                        time_cursor += 1

                    start_time = sub_chars[0][1]
                    end_time = sub_chars[-1][2]
                    segments.append({
                        "text": part,
                        "start_time": start_time,
                        "end_time": end_time
                    })

                break
        else:
            logger.warning(f"LLM 查询失败，重试 {llm_retry} 次后仍未成功，使用语音停顿和语义边界进行切分。")

            match_result = re.search(chunk_without_spaces, full_text_without_spaces)
            assert match_result, "匹配不到原始文本中的内容，请检查切分逻辑。"

            start_index = match_result.start()
            end_index = match_result.end()

            chunk_segments = split_by_pause_and_semantics(
                char_time_list=char_time_list[start_index:end_index],
                pause_threshold=0.6,
                max_chars=max_char_per_seg
            )

            segments.extend(chunk_segments)

    return segments


def run_asr_on_slices_by_sense_voice(audio_path, batch_size_s):
    model_dir = "iic/SenseVoiceSmall"
    m, kwargs = SenseVoiceSmall.from_pretrained(model=model_dir, device="cuda:0")
    m.eval()

    slices = slice_audio(audio_path, batch_size_s=batch_size_s)

    all_results = []
    if not os.path.exists("./temp"):
        os.makedirs("./temp")

    for idx, (audio_tensor, t_start, t_end) in enumerate(slices):
        logger.info(f"Processing slice {idx + 1}/{len(slices)}: {t_start:.2f}s - {t_end:.2f}s")

        temp_path = f"./temp/clip_{idx}.wav"
        sf.write(temp_path, audio_tensor.T.numpy(), samplerate=16000, format='WAV', subtype='PCM_16')

        try:
            with torch.no_grad():
                res = m.inference(
                    data_in=temp_path,
                    language="auto",
                    use_itn=False,
                    ban_emo_unk=True,
                    output_timestamp=True,
                    **kwargs,
                )
        except Exception as e:
            logger.error(f"Error processing slice {idx + 1}: {e}")
            logger.warning("Skipping this slice.")
            continue

        fix_str = lambda s: s.replace("_", "").replace("▁", "")

        for item in res[0]:
            # 修正时间戳为全局时间
            new_item = {
                "text": fix_str(item["text"]),
                "timestamp": [
                    [fix_str(lst[0]), round(lst[1] + t_start, 2), round(lst[2] + t_start, 2)]
                    for lst in item["timestamp"] if fix_str(lst[0]) != ""
                ]
            }
            all_results.append(new_item)

    # 清理临时文件
    for idx in range(len(slices)):
        temp_path = f"./temp/clip_{idx}.wav"
        if os.path.exists(temp_path):
            os.remove(temp_path)

    zipped_results = {
        "text": clean_asr_text("".join(item["text"] for item in all_results)),
        "timestamp": sum([item["timestamp"] for item in all_results], start=[])
    }

    return zipped_results


def run_asr_by_paraformer(audio_path):
    model_paraformer = get_paraformer_model()
    res = model_paraformer.generate(
        input=audio_path,
        batch_size_s=900,
    )

    text = res[0]["text"]
    timestamp = []
    for begin, end in res[0]["timestamp"]:
        timestamp.append([begin / 1000, end / 1000])  # 转为秒

    return {
        "text": text,
        "timestamp": timestamp
    }


def seconds_to_timestamp(seconds, file_type='srt'):
    """
    将秒转换为 SRT 或 CC 格式的时间戳字符串
    :param seconds: 秒数
    :param file_type: 'srt' 或 'cc'
    :return: 格式化的时间戳字符串
    """
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    milliseconds = int((td.total_seconds() - total_seconds) * 1000)

    if file_type == 'srt':
        return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"
    elif file_type == 'cc':
        return f"{hours:02}:{minutes:02}:{secs:02}.{milliseconds:04}"
    else:
        raise ValueError("Unsupported file type. Use 'srt' or 'cc'.")


def gen_timestamped_text_from_data(segments_data, file_type='srt') -> str:
    """
    生成带时间戳的文本字符串（.srt 或 .cc）。

    :param segments_data: 包含时间戳和文本的字典
    :param file_type: 输出文件类型，'srt' 或 'cc'
    :return: 生成的带时间戳的文本字符串
    """
    lines = []

    for idx, segment in enumerate(segments_data):
        start_time = seconds_to_timestamp(segment["start_time"], file_type=file_type)
        end_time = seconds_to_timestamp(segment["end_time"], file_type=file_type)
        text = segment["text"].strip()

        if file_type == 'srt':
            lines.append(f"{idx + 1}")
            lines.append(f"{start_time} --> {end_time}")
            lines.append(text)
            lines.append("")  # 空行分隔
        elif file_type == 'cc':
            lines.append(f"{start_time} {end_time} {text}")

    return "\n".join(lines)


def gen_timestamped_text_file(audio_path: str, file_type: str = 'srt', batch_size_s: int = 5,
                              model: str = 'paraformer') -> str:
    """
    生成带时间戳的字幕文件（.srt 或 .cc）。

    :param audio_path: 输入音频文件路径
    :param file_type: 输出文件类型，'srt' 或 'cc'
    :param batch_size_s: 每个批次处理的音频长度（秒）
    :param model: 使用的 ASR 模型，'paraformer' 或 'sense_voice'
    :return: 生成的字幕文件路径
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"未找到音频文件：{audio_path}")

    if model == 'sense_voice':
        timestamp_data = run_asr_on_slices_by_sense_voice(audio_path, batch_size_s=batch_size_s)
    elif model == 'paraformer':
        timestamp_data = run_asr_by_paraformer(audio_path)
    else:
        raise ValueError(f"不支持的模型类型：{model}")

    if not timestamp_data["timestamp"]:
        raise ValueError("未能从音频中提取到任何字幕信息。")

    timestamp_data = split_by_pause_and_semantics(timestamp_data)
    output_text = gen_timestamped_text_from_data(timestamp_data, file_type=file_type)
    output_file = f"{os.path.splitext(audio_path)[0]}.{file_type}"
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write(output_text)

    return output_file


def hard_encode_dot_srt_file(input_video_path: str, input_srt_path: str, output_video_path: str = None) -> str:
    """
    将 .srt 字幕文件硬编码到视频中。

    :param input_video_path: 输入视频路径
    :param input_srt_path: 输入 .srt 字幕文件路径
    :param output_video_path: 输出视频路径（硬编码字幕后）
    :return: 输出视频路径
    """
    if not os.path.isfile(input_video_path):
        raise FileNotFoundError(f"未找到视频文件：{input_video_path}")
    if not os.path.isfile(input_srt_path):
        raise FileNotFoundError(f"未找到字幕文件：{input_srt_path}")
    if output_video_path is None:
        output_video_path = os.path.splitext(input_video_path)[0] + "-with-subtitles.mp4"

    # Windows 下 ffmpeg 要求路径中的 ":" 进行转义，斜杠统一用 /
    def escape_path(path: str) -> str:
        return path.replace("\\", "/").replace(":", "\\\\:")

    input_video_ffmpeg = input_video_path.replace("\\", "/")
    input_srt_ffmpeg = escape_path(input_srt_path)
    output_video_ffmpeg = output_video_path.replace("\\", "/")

    command = [
        'ffmpeg',
        '-i', input_video_ffmpeg,
        '-vf', f'subtitles={input_srt_ffmpeg}',
        '-c:a', 'copy',
        '-y',
        output_video_ffmpeg
    ]

    logger.info(f"开始硬编码字幕到视频：{output_video_path}")
    logger.debug(f"{' '.join(command)}")

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

    if result.returncode != 0:
        raise RuntimeError(f"字幕硬编码失败：\n{result.stderr}")

    logger.info(f"字幕硬编码成功，输出视频路径：{output_video_path}")
    return output_video_path


if __name__ == "__main__":
    from src.bilibili_downloader import extract_audio_from_video, download_bilibili_video
    from config import DOWNLOAD_DIR

    using_local_video = input("是否使用本地视频文件？(y/n)：\n").strip().lower()

    if using_local_video == "y":
        video_path = input("请输入本地视频文件路径：\n").strip()
        if not os.path.isfile(video_path):
            logger.error(f"未找到视频文件：{video_path}")
            sys.exit(1)
    else:
        video_url = input("请输入B站视频链接（例如：https://www.bilibili.com/video/BV1...）：\n")
        video_path = download_bilibili_video(video_url, output_format='mp4', output_dir=DOWNLOAD_DIR)

    video_path = "temp/test_video.mp4"

    audio_path = extract_audio_from_video(video_path, output_format='mp3', output_dir=DOWNLOAD_DIR)

    gen_file_type = input("请输入生成的字幕文件类型（cc/srt）[默认为srt]：\n").strip().lower()
    if gen_file_type not in ["cc", "srt"]:
        gen_file_type = "srt"

    file_path = gen_timestamped_text_file(audio_path, file_type=gen_file_type, batch_size_s=5)
    logger.info(f"字幕文件已生成：{file_path}")

    if gen_file_type == "srt":
        hard_encode_flag = input("是否将字幕硬编码到视频中？(y/n)：\n").strip().lower()
        if hard_encode_flag == "y":
            output_video_path = os.path.splitext(video_path)[0] + "-subtitled.mp4"
            hard_encode_dot_srt_file(video_path, file_path, output_video_path)
            logger.info(f"硬编码字幕后的视频已保存到：{output_video_path}")
        else:
            logger.info("字幕文件已生成，但未进行硬编码。")
