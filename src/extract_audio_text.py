from funasr import AutoModel

from src.text_arrangement.split_text import clean_asr_text

model_dir_sense_voice_small = "iic/SenseVoiceSmall"

model_sense_voice_small = AutoModel(
    model=model_dir_sense_voice_small,
    trust_remote_code=True,
    remote_code="./src/SenseVoiceSmall/model.py",
    vad_model="fsmn-vad",
    vad_kwargs={"max_single_segment_time": 30000},
    device="cuda:0",
    disable_update=True,
)


def extract_audio_text_by_sense_voice(input_audio_path: str, language: str = "auto") -> str:
    """
    提取音频文本
    :param input_audio_path: 输入音频文件路径
    :param language: 语言类型，支持 "auto", "zh", "en", "yue", "ja", "ko", "nospeech"
    :return: 提取的文本
    """
    support_languages = ["auto", "zh", "en", "yue", "ja", "ko", "nospeech"]

    if language not in support_languages:
        raise ValueError(f"Language '{language}' is not supported. Supported languages are: {support_languages}")

    # Generate transcription
    res = model_sense_voice_small.generate(
        input=input_audio_path,
        cache={},
        language=language,  # "zh", "en", "yue", "ja", "ko", "nospeech"
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )

    # Post-process the transcription
    text = clean_asr_text(res[0]["text"])
    return text


model_paraformer = AutoModel(model="paraformer-zh", model_revision="v2.0.4",
                             vad_model="fsmn-vad", vad_model_revision="v2.0.4",
                             punc_model="ct-punc-c", punc_model_revision="v2.0.4",
                             # spk_model="cam++", spk_model_revision="v2.0.2",
                             )


def extract_audio_text_by_paraformer(input_audio_path: str, language: str = "auto") -> str:
    return model_paraformer.generate(
        input=input_audio_path,
        batch_size_s=300,
    )
