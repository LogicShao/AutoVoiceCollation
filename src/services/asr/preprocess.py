"""
ASR 音频预处理

将输入音频统一转换为 16kHz / mono / PCM WAV (16-bit)。
"""

from __future__ import annotations

import subprocess
import time
import uuid
from pathlib import Path

import soundfile as sf

from src.core.exceptions import ASRInferenceError, AudioFormatError, TaskCancelledException
from src.utils.config import get_config
from src.utils.helpers.task_manager import get_task_manager
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

_TARGET_SAMPLE_RATE = 16000
_TARGET_CHANNELS = 1
_TARGET_SUBTYPE = "PCM_16"


def _is_target_wav(path: Path) -> bool:
    try:
        info = sf.info(str(path))
    except Exception:
        return False
    return (
        info.samplerate == _TARGET_SAMPLE_RATE
        and info.channels == _TARGET_CHANNELS
        and info.subtype == _TARGET_SUBTYPE
    )


def _read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def prepare_asr_audio(audio_path: str, task_id: str | None = None) -> tuple[Path, bool]:
    """
    ????????? 16kHz / mono / PCM_16 WAV?
    Returns:
        (??????, ???????)
    """
    source = Path(audio_path)
    if not source.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if source.suffix.lower() == ".wav" and _is_target_wav(source):
        return source, False

    config = get_config()
    temp_dir = (config.paths.temp_dir or Path("./temp")) / "asr_preprocess"
    temp_dir.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    output_wav = temp_dir / f"{source.stem}.{run_id}.wav"
    stdout_path = temp_dir / f"{source.stem}.{run_id}.ffmpeg.stdout.txt"
    stderr_path = temp_dir / f"{source.stem}.{run_id}.ffmpeg.stderr.txt"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ar",
        str(_TARGET_SAMPLE_RATE),
        "-ac",
        str(_TARGET_CHANNELS),
        "-c:a",
        "pcm_s16le",
        str(output_wav),
    ]

    task_manager = get_task_manager() if task_id else None
    try:
        if task_id:
            task_manager.check_cancellation(task_id)

        with (
            open(stdout_path, "wb") as stdout_f,
            open(stderr_path, "wb") as stderr_f,
        ):
            proc = subprocess.Popen(
                cmd,
                stdout=stdout_f,
                stderr=stderr_f,
            )

            try:
                while True:
                    if task_id:
                        task_manager.check_cancellation(task_id)
                    ret = proc.poll()
                    if ret is not None:
                        break
                    time.sleep(0.2)
            except TaskCancelledException:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
                _safe_unlink(output_wav)
                _safe_unlink(stdout_path)
                _safe_unlink(stderr_path)
                raise

            if ret != 0:
                _safe_unlink(output_wav)
                stderr_tail = _read_text_safely(stderr_path)
                raise ASRInferenceError(
                    message=f"ffmpeg ???????: {stderr_tail}",
                    model="preprocess",
                    audio_file=str(source),
                )
    except FileNotFoundError as e:
        _safe_unlink(output_wav)
        raise AudioFormatError(
            message=("??? ffmpeg????? ASR ????????? ffmpeg ??? 16kHz ??? PCM WAV (16-bit) ???"),
            audio_file=str(source),
            format=source.suffix,
        ) from e
    finally:
        if not config.debug_flag:
            _safe_unlink(stdout_path)
            _safe_unlink(stderr_path)

    if not output_wav.exists():
        raise ASRInferenceError(
            message="ffmpeg ?????? wav ??",
            model="preprocess",
            audio_file=str(source),
        )

    logger.info(f"ASR ?????: {source} -> {output_wav}")
    return output_wav, True


def cleanup_preprocessed_audio(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
