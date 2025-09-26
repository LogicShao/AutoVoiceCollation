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


def extract_audio_text_by_sense_voice(input_audio_path: str) -> str:
    """
    提取音频文本 (SenseVoiceSmall)
    """
    res = model_sense_voice_small.generate(
        input=input_audio_path,
        cache={},
        language="auto",  # "zh", "en", "yue", "ja", "ko", "nospeech"
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )

    text = clean_asr_text(res[0]["text"])
    return text


model_paraformer = AutoModel(
    model="paraformer-zh",
    model_revision="v2.0.4",
    vad_model="fsmn-vad",
    vad_model_revision="v2.0.4",
    punc_model="ct-punc-c",
    punc_model_revision="v2.0.4",
    # spk_model="cam++", spk_model_revision="v2.0.2",
    device="cuda:0",
    disable_update=True,
)


def extract_audio_text_by_paraformer(input_audio_path: str) -> str:
    """
    提取音频文本 (Paraformer)
    """
    res = model_paraformer.generate(
        input=input_audio_path,
        batch_size_s=600,
    )
    return res[0]["text"]


def extract_audio_text(input_audio_path: str, model_type: str = "paraformer") -> str:
    """
    提取音频文本
    """
    print(f"Extracting text from audio: {input_audio_path} using model: {model_type}")

    if model_type == "sense_voice":
        return extract_audio_text_by_sense_voice(input_audio_path)
    elif model_type == "paraformer":
        return extract_audio_text_by_paraformer(input_audio_path)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
