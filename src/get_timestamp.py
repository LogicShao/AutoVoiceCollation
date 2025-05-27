import os
import sys

sys.path.append("./SenseVoice")

import soundfile as sf
import torch
import torchaudio
from funasr.utils.postprocess_utils import rich_transcription_postprocess
from SenseVoice.model import SenseVoiceSmall
from datetime import timedelta


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

    print(f"Total slices: {len(slices)}")
    return slices


def run_asr_on_slices(audio_path, batch_size_s):
    model_dir = "iic/SenseVoiceSmall"
    m, kwargs = SenseVoiceSmall.from_pretrained(model=model_dir, device="cuda:0")
    m.eval()

    slices = slice_audio(audio_path, batch_size_s=batch_size_s)

    all_results = []
    if not os.path.exists("./temp"):
        os.makedirs("./temp")

    for idx, (audio_tensor, t_start, t_end) in enumerate(slices):
        print(f"Processing slice {idx + 1}/{len(slices)}: {t_start:.2f}s - {t_end:.2f}s")

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
            print(f"Error processing slice {idx + 1}: {e}")
            print("Skipping this slice.")
            continue

        for item in res[0]:
            # 修正时间戳为全局时间
            new_item = {
                "text": rich_transcription_postprocess(item["text"]),
                "timestamp": [
                    [lst[0], round(lst[1] + t_start, 2), round(lst[2] + t_start, 2)] for lst in item["timestamp"]
                ]
            }
            all_results.append(new_item)

    # 清理临时文件
    for idx in range(len(slices)):
        temp_path = f"./temp/clip_{idx}.wav"
        if os.path.exists(temp_path):
            os.remove(temp_path)

    zipped_results = {
        "text": "".join(item["text"].replace("_", "").replace("▁", "") for item in all_results),
        "timestamp": sum(
            [list(map(lambda lst: [lst[0].replace("_", "").replace("▁", ""), *lst[1::]], item["timestamp"])) for item in
             all_results],
            start=[])
    }

    return zipped_results


def seconds_to_timestamp(seconds):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    milliseconds = int((td.total_seconds() - total_seconds) * 1000)

    return f"{hours:02}:{minutes:02}:{secs:02}.{milliseconds:04}"


def generate_webvtt_cc(sub_dict, max_chars_per_line=12):
    lines = ["WEBVTT\n"]
    index = 1
    buffer = ""
    start_time = None
    end_time = None

    for i, (char, start, end) in enumerate(sub_dict["timestamp"]):
        if start_time is None:
            start_time = start
        buffer += char
        end_time = end

        # 条件：超出字符数或是结尾
        if len(buffer) >= max_chars_per_line or i == len(sub_dict["timestamp"]) - 1:
            start_str = seconds_to_timestamp(start_time)
            end_str = seconds_to_timestamp(end_time)
            lines.append(f"{index}")
            lines.append(f"{start_str} --> {end_str}")
            lines.append(buffer)
            lines.append("")  # 空行分割
            index += 1
            buffer = ""
            start_time = None

    return "\n".join(lines)


def save_dot_cc_file(sub_dict, filename="output.cc"):
    """
    保存字典内容为 .cc 文件
    :param sub_dict: 包含文本和时间戳的字典
    :param filename: 输出文件名
    """
    with open(filename, "w", encoding="utf-8-sig") as f:
        f.write(generate_webvtt_cc(sub_dict))


def gen_dot_cc_file(audio_path: str, batch_size_s: int = 5, output_file: str = None):
    """
    生成 .cc 字幕文件
    :param audio_path: 音频文件路径
    :param batch_size_s: 每个切片的时长（秒）
    :param output_file: 输出的 .cc 文件名
    """
    if output_file is None:
        output_file = os.path.splitext(audio_path)[0] + ".cc"

    res_dict = run_asr_on_slices(audio_path, batch_size_s)
    save_dot_cc_file(res_dict, filename=output_file)
    print(f"字幕文件已保存到：{output_file}")


def seconds_to_srt_timestamp(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    milliseconds = int((td.total_seconds() - total_seconds) * 1000)

    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def save_dot_srt_file(res_dict, filename):
    """
    保存为 .srt 字幕文件
    :param res_dict: 包含 "text" 和 "timestamp" 的识别结果字典
    :param filename: 输出文件名
    """
    lines = []
    index = 1
    buffer = ""
    start_time = None
    end_time = None
    max_chars_per_line = 12  # 每条字幕最多字符数，可根据需要调整

    for i, (char, start, end) in enumerate(res_dict["timestamp"]):
        if start_time is None:
            start_time = start
        buffer += char
        end_time = end

        # 生成一条字幕
        if len(buffer) >= max_chars_per_line or i == len(res_dict["timestamp"]) - 1:
            start_str = seconds_to_srt_timestamp(start_time)
            end_str = seconds_to_srt_timestamp(end_time)
            lines.append(f"{index}")
            lines.append(f"{start_str} --> {end_str}")
            lines.append(buffer)
            lines.append("")
            index += 1
            buffer = ""
            start_time = None

    with open(filename, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


def gen_dot_srt_file(audio_path: str, batch_size_s: int = 5, output_file: str = None):
    """
    生成 .srt 字幕文件
    :param audio_path: 音频文件路径
    :param batch_size_s: 每个切片的时长（秒）
    :param output_file: 输出的 .srt 文件名
    """
    if output_file is None:
        output_file = os.path.splitext(audio_path)[0] + ".srt"

    res_dict = run_asr_on_slices(audio_path, batch_size_s)
    save_dot_srt_file(res_dict, filename=output_file)
    print(f"字幕文件已保存到：{output_file}")


# 用法示例
if __name__ == "__main__":
    audio_path = ""
    batch_size_s = 5

    gen_dot_cc_file(audio_path, batch_size_s)
