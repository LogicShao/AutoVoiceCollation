from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

model_dir = "iic/SenseVoiceSmall"
support_languages = ["auto", "zh", "en", "yue", "ja", "ko", "nospeech"]

model = AutoModel(
    model=model_dir,
    trust_remote_code=True,
    remote_code="./SenseVoice/model.py",
    vad_model="fsmn-vad",
    vad_kwargs={"max_single_segment_time": 30000},
    device="cuda:0",
    disable_update=True,
)


def extract_audio_text(input_audio_path: str, language: str = "auto") -> str:
    """
    提取音频文本
    :param input_audio_path: 输入音频文件路径
    :param language: 语言类型，支持 "auto", "zh", "en", "yue", "ja", "ko", "nospeech"
    :return: 提取的文本
    """
    if language not in support_languages:
        raise ValueError(f"Language '{language}' is not supported. Supported languages are: {support_languages}")

    # Generate transcription
    res = model.generate(
        input=input_audio_path,
        cache={},
        language=language,  # "zh", "en", "yue", "ja", "ko", "nospeech"
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )

    # Post-process the transcription
    text = rich_transcription_postprocess(res[0]["text"])
    return text
