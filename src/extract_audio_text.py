from typing import Optional

from funasr import AutoModel

from config import MODEL_DIR, THIRD_PARTY_LOG_LEVEL
from src.logger import get_logger, configure_third_party_loggers
from src.text_arrangement.split_text import clean_asr_text

logger = get_logger(__name__)

# 配置第三方库日志级别，避免输出过多信息
configure_third_party_loggers(THIRD_PARTY_LOG_LEVEL)

# 模型缓存
_model_sense_voice_small: Optional[AutoModel] = None
_model_paraformer: Optional[AutoModel] = None


def get_sense_voice_model() -> AutoModel:
    """
    延迟加载 SenseVoiceSmall 模型
    """
    global _model_sense_voice_small
    if _model_sense_voice_small is None:
        try:
            logger.info("Loading SenseVoiceSmall model...")
            model_dir_sense_voice_small = "iic/SenseVoiceSmall"
            _model_sense_voice_small = AutoModel(
                model=model_dir_sense_voice_small,
                trust_remote_code=True,
                remote_code="./src/SenseVoiceSmall/model.py",
                vad_model="fsmn-vad",
                vad_kwargs={"max_single_segment_time": 30000},
                device="cuda:0",
                disable_update=True,
                model_hub="huggingface",
                cache_dir=MODEL_DIR,
            )
            logger.info("SenseVoiceSmall model loaded successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to load SenseVoiceSmall model: {e}")
    return _model_sense_voice_small


def get_paraformer_model() -> AutoModel:
    """
    延迟加载 Paraformer 模型
    """
    global _model_paraformer
    if _model_paraformer is None:
        try:
            logger.info("Loading Paraformer model...")
            _model_paraformer = AutoModel(
                model="paraformer-zh",
                model_revision="v2.0.4",
                vad_model="fsmn-vad",
                vad_model_revision="v2.0.4",
                punc_model="ct-punc-c",
                punc_model_revision="v2.0.4",
                device="cuda:0",
                disable_update=True,
                model_hub="huggingface",
                cache_dir=MODEL_DIR,
            )
            logger.info("Paraformer model loaded successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to load Paraformer model: {e}")
    return _model_paraformer


def extract_audio_text_by_sense_voice(input_audio_path: str) -> str:
    """
    提取音频文本 (SenseVoiceSmall)
    """
    model = get_sense_voice_model()
    try:
        res = model.generate(
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
    except Exception as e:
        raise RuntimeError(f"Failed to extract audio text with SenseVoice: {e}")


def extract_audio_text_by_paraformer(input_audio_path: str) -> str:
    """
    提取音频文本 (Paraformer)
    """
    model = get_paraformer_model()
    try:
        res = model.generate(
            input=input_audio_path,
            batch_size_s=600,
        )
        return res[0]["text"]
    except Exception as e:
        raise RuntimeError(f"Failed to extract audio text with Paraformer: {e}")


def extract_audio_text(input_audio_path: str, model_type: str = "paraformer") -> str:
    """
    提取音频文本
    :param input_audio_path: 输入音频文件路径
    :param model_type: 模型类型 ("sense_voice" 或 "paraformer")
    :return: 提取的文本
    :raises ValueError: 不支持的模型类型
    :raises RuntimeError: 模型加载或推理失败
    """
    logger.info(f"Extracting text from audio: {input_audio_path} using model: {model_type}")

    if model_type == "sense_voice":
        return extract_audio_text_by_sense_voice(input_audio_path)
    elif model_type == "paraformer":
        return extract_audio_text_by_paraformer(input_audio_path)
    else:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: 'sense_voice', 'paraformer'")
