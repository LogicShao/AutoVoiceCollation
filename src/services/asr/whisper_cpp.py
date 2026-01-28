"""
whisper.cpp ASR 服务

通过调用本地 whisper.cpp 的 whisper-cli.exe 进行转写。
"""

from __future__ import annotations

import io
import os
import re
import shlex
import subprocess
import threading
import time
import uuid
from pathlib import Path

from src.core.exceptions import (
    ASRInferenceError,
    ASRModelLoadError,
    AudioFormatError,
    TaskCancelledException,
)
from src.utils.config import get_config

from .base import BaseASRService


class WhisperCppService(BaseASRService):
    """whisper.cpp ASR 服务（通过命令行调用）"""

    _SUPPORTED_AUDIO_EXTS = {".flac", ".mp3", ".ogg", ".wav"}
    _PROGRESS_RE = re.compile(r"\bprogress\s*=\s*([0-9]{1,3})%")

    def __init__(self):
        super().__init__()
        self._validated = False
        self._bin_path: Path | None = None
        self._model_path: Path | None = None

    def load_model(self):
        """
        whisper.cpp 不需要在 Python 侧加载模型，这里仅做路径校验。
        """
        if self._validated:
            return

        config = get_config()
        project_root = config.asr.get_project_root()

        bin_path = config.asr.whisper_cpp_bin or (
            project_root / "assets" / "whisper.cpp" / "whisper-cli.exe"
        )
        model_path = config.asr.whisper_cpp_model or (
            project_root / "assets" / "models" / "ggml-medium-q5_0.bin"
        )

        if not bin_path.exists():
            raise ASRModelLoadError(
                f"未找到 whisper.cpp 可执行文件: {bin_path}。请在 .env 中设置 WHISPER_CPP_BIN",
                model="whisper_cpp",
            )

        if not model_path.exists():
            raise ASRModelLoadError(
                f"未找到 whisper.cpp 模型文件: {model_path}。请在 .env 中设置 WHISPER_CPP_MODEL",
                model="whisper_cpp",
            )

        vad_model_path = config.asr.whisper_cpp_vad_model
        vad_enabled = bool(config.asr.whisper_cpp_vad) or vad_model_path is not None

        if vad_model_path is not None and not vad_model_path.exists():
            raise ASRModelLoadError(
                f"未找到 whisper.cpp VAD 模型文件: {vad_model_path}。请在 .env 中设置 WHISPER_CPP_VAD_MODEL",
                model="whisper_cpp",
            )

        if vad_enabled and vad_model_path is None:
            extra_args = self._split_args(config.asr.whisper_cpp_extra_args)
            has_vad_model_arg = "--vad-model" in extra_args or "-vm" in extra_args
            if not has_vad_model_arg:
                raise ASRModelLoadError(
                    "已启用 whisper.cpp VAD，但未提供 VAD 模型。请在 .env 中设置 WHISPER_CPP_VAD_MODEL，"
                    "或在 WHISPER_CPP_EXTRA_ARGS 中传入 --vad-model/-vm。",
                    model="whisper_cpp",
                )

        self._bin_path = bin_path
        self._model_path = model_path
        self._validated = True

    def transcribe(self, audio_path: str, task_id: str | None = None) -> str:
        # 任务取消检查（模型校验前）
        self.check_cancellation(task_id)

        # 校验 bin/model 路径
        self.load_model()

        # 任务取消检查（推理前）
        self.check_cancellation(task_id)

        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        config = get_config()
        temp_dir = (config.paths.temp_dir or Path("./temp")) / "whisper_cpp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        run_id = uuid.uuid4().hex
        output_base = temp_dir / f"{audio_file.stem}.{run_id}"
        output_txt = Path(f"{output_base}.txt")
        stdout_path = temp_dir / f"{audio_file.stem}.{run_id}.stdout.txt"
        stderr_path = temp_dir / f"{audio_file.stem}.{run_id}.stderr.txt"

        input_for_whisper = self._prepare_input_audio(audio_file, temp_dir, run_id)

        cmd = self._build_command(
            input_audio=input_for_whisper,
            output_base=output_base,
        )

        try:
            with (
                open(stdout_path, "wb") as stdout_f,
                open(stderr_path, "w", encoding="utf-8", errors="replace") as stderr_f,
            ):
                proc = subprocess.Popen(
                    cmd,
                    stdout=stdout_f,
                    stderr=subprocess.PIPE,
                )

                stderr_thread = None
                stderr_stream = proc.stderr
                if stderr_stream is not None:
                    stderr_thread = threading.Thread(
                        target=self._stream_stderr_with_progress,
                        args=(stderr_stream, stderr_f, task_id),
                        daemon=True,
                    )
                    stderr_thread.start()

                while True:
                    try:
                        self.check_cancellation(task_id)
                    except TaskCancelledException:
                        proc.terminate()
                        try:
                            proc.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=2)
                        if stderr_thread is not None:
                            stderr_thread.join(timeout=2)
                        raise

                    ret = proc.poll()
                    if ret is not None:
                        break
                    time.sleep(0.2)

                if stderr_thread is not None:
                    stderr_thread.join(timeout=5)

                if ret != 0:
                    stderr_tail = self._read_text_safely(stderr_path)
                    raise ASRInferenceError(
                        message=(
                            "whisper.cpp 推理失败。"
                            f"exit_code={ret}, audio={audio_file}\n"
                            f"stderr:\n{stderr_tail}"
                        ),
                        model="whisper_cpp",
                        audio_file=str(audio_file),
                    )

            if not output_txt.exists():
                stderr_tail = self._read_text_safely(stderr_path)
                raise ASRInferenceError(
                    message=(
                        "whisper.cpp 未生成输出文本文件。"
                        f"expected={output_txt}, audio={audio_file}\n"
                        f"stderr:\n{stderr_tail}"
                    ),
                    model="whisper_cpp",
                    audio_file=str(audio_file),
                )

            return self._read_text_safely(output_txt).strip()

        finally:
            if not config.debug_flag:
                self._cleanup_temp_files(
                    original_audio=audio_file,
                    input_audio=input_for_whisper,
                    output_txt=output_txt,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                )

    def _stream_stderr_with_progress(
        self,
        stderr_stream,
        stderr_file,
        task_id: str | None,
    ) -> None:
        """
        从 whisper-cli 的 stderr 读取输出，写入 stderr 文件，并将进度打印到日志。

        进度日志默认按 5% 步进输出，避免刷屏。
        """
        last_logged_bucket = -1
        try:
            text_stream = io.TextIOWrapper(stderr_stream, encoding="utf-8", errors="replace")
            for line in text_stream:
                try:
                    stderr_file.write(line)
                    stderr_file.flush()
                except Exception:
                    pass

                progress = self._parse_progress_percent(line)
                if progress is None:
                    continue
                if progress < 0 or progress > 100:
                    continue

                # 5% 步进输出，避免刷屏
                bucket = min(100, (progress // 5) * 5)
                if bucket > last_logged_bucket:
                    last_logged_bucket = bucket
                    suffix = f" (task_id={task_id})" if task_id else ""
                    self.logger.info(f"whisper.cpp progress: {bucket}%{suffix}")
        except Exception:
            # stderr 输出解析失败不应影响主流程
            return

    @classmethod
    def _parse_progress_percent(cls, line: str) -> int | None:
        m = cls._PROGRESS_RE.search(line)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    def _build_command(self, input_audio: Path, output_base: Path) -> list[str]:
        config = get_config()
        bin_path = self._bin_path
        model_path = self._model_path
        if bin_path is None or model_path is None:
            raise ASRModelLoadError("whisper.cpp 未正确初始化", model="whisper_cpp")

        extra_args = self._split_args(config.asr.whisper_cpp_extra_args)
        extra_args = self._ensure_vad_args(extra_args)
        extra_args = self._ensure_progress_args(extra_args)
        language = (config.asr.whisper_cpp_language or "auto").strip().lower()
        threads = int(config.asr.whisper_cpp_threads)

        cmd = [
            str(bin_path),
            "-m",
            str(model_path),
            "-t",
            str(threads),
            "-l",
            language,
            "-otxt",
            "-of",
            str(output_base),
            str(input_audio),
        ]
        return cmd[:1] + extra_args + cmd[1:]

    @staticmethod
    def _ensure_progress_args(extra_args: list[str]) -> list[str]:
        # 用户显式关闭输出时，不强行开启进度
        if "-np" in extra_args or "--no-prints" in extra_args:
            return extra_args

        if "-pp" in extra_args or "--print-progress" in extra_args:
            return extra_args

        # 默认开启进度输出
        return ["-pp", *extra_args]

    @staticmethod
    def _ensure_vad_args(extra_args: list[str]) -> list[str]:
        """
        根据 .env 配置自动注入 VAD 参数。

        规则：
        - 只要设置了 WHISPER_CPP_VAD_MODEL，就自动启用 VAD
        - 若用户在 WHISPER_CPP_EXTRA_ARGS 中已显式传入 --vad/--vad-model/-vm，则不重复注入
        """
        config = get_config()
        vad_model = config.asr.whisper_cpp_vad_model
        vad_enabled = bool(config.asr.whisper_cpp_vad) or vad_model is not None
        if not vad_enabled:
            return extra_args

        has_vad_flag = "--vad" in extra_args
        has_vad_model_flag = "--vad-model" in extra_args or "-vm" in extra_args

        inject: list[str] = []
        if not has_vad_flag:
            inject.append("--vad")
        if vad_model is not None and not has_vad_model_flag:
            inject.extend(["--vad-model", str(vad_model)])

        return [*inject, *extra_args]

    def _prepare_input_audio(self, audio_file: Path, temp_dir: Path, run_id: str) -> Path:
        """
        whisper-cli.exe 的 help 声明支持 flac/mp3/ogg/wav。
        对其它格式尝试用 ffmpeg 转成 16k 单声道 wav（若 ffmpeg 不存在则报错）。
        """
        if audio_file.suffix.lower() in self._SUPPORTED_AUDIO_EXTS:
            return audio_file

        output_wav = temp_dir / f"{audio_file.stem}.{run_id}.wav"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_file),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(output_wav),
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as e:
            raise AudioFormatError(
                message=(
                    f"音频格式 {audio_file.suffix} 可能不被 whisper.cpp 直接支持，"
                    "且未找到 ffmpeg，无法自动转码。请先转为 wav/mp3/flac/ogg。"
                ),
                audio_file=str(audio_file),
                format=audio_file.suffix,
            ) from e
        except subprocess.CalledProcessError as e:
            raise ASRInferenceError(
                message=f"ffmpeg 转码失败: {e.stderr or e.stdout}",
                model="whisper_cpp",
                audio_file=str(audio_file),
            ) from e

        if not output_wav.exists():
            raise ASRInferenceError(
                message="ffmpeg 未生成预期的 wav 文件",
                model="whisper_cpp",
                audio_file=str(audio_file),
            )

        return output_wav

    @staticmethod
    def _split_args(extra_args: str) -> list[str]:
        if not extra_args or not extra_args.strip():
            return []
        posix = os.name != "nt"
        return shlex.split(extra_args, posix=posix)

    @staticmethod
    def _read_text_safely(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _cleanup_temp_files(
        original_audio: Path,
        input_audio: Path,
        output_txt: Path,
        stdout_path: Path,
        stderr_path: Path,
    ) -> None:
        for p in [output_txt, stdout_path, stderr_path]:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        # 删除自动转码生成的 wav（仅当它不是原始输入）
        try:
            if input_audio != original_audio and input_audio.exists():
                input_audio.unlink()
        except Exception:
            pass
