import base64
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

from django.conf import settings

DEFAULT_SPEECH_LANG = "en-US"
DEFAULT_SPEECH_SPEED = 1.0
MIN_SPEECH_SPEED = 0.5
MAX_SPEECH_SPEED = 1.2
MAX_SPEECH_TEXT_LENGTH = 400


class SpeechSynthesisError(RuntimeError):
    pass


def _normalize_text(text):
    content = " ".join(str(text or "").split()).strip()
    if not content:
        raise ValueError("朗读内容为空")
    if len(content) > MAX_SPEECH_TEXT_LENGTH:
        raise ValueError(f"朗读内容不能超过 {MAX_SPEECH_TEXT_LENGTH} 个字符")
    return content


def _normalize_lang(lang):
    value = str(lang or DEFAULT_SPEECH_LANG).strip()
    return value or DEFAULT_SPEECH_LANG


def _normalize_speed(speed):
    try:
        value = float(speed)
    except (TypeError, ValueError):
        value = DEFAULT_SPEECH_SPEED
    value = min(max(value, MIN_SPEECH_SPEED), MAX_SPEECH_SPEED)
    return round(value, 2)


def _speech_speed_to_sapi_rate(speed):
    return min(max(int(round((speed - 1.0) * 10)), -10), 10)


def _detect_culture_prefix(lang):
    lowered = str(lang or "").lower()
    if lowered.startswith("zh"):
        return "zh"
    return "en"


def _get_output_path(text, lang, speed):
    digest = hashlib.sha1(f"{lang}\n{speed:.2f}\n{text}".encode("utf-8")).hexdigest()
    output_dir = Path(settings.MEDIA_ROOT) / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{digest}.wav"


def _encode_powershell_command(script):
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def _build_windows_speech_command(text, lang, speed, output_path):
    culture_prefix = _detect_culture_prefix(lang)
    sapi_rate = _speech_speed_to_sapi_rate(speed)
    script = dedent(
        f"""
        $ErrorActionPreference = 'Stop'
        Add-Type -AssemblyName System.Speech
        $text = {json.dumps(text)}
        $outputPath = {json.dumps(str(output_path))}
        $directory = Split-Path -Parent $outputPath
        if (-not (Test-Path $directory)) {{
          New-Item -ItemType Directory -Path $directory -Force | Out-Null
        }}

        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        try {{
          $preferredVoice = $synth.GetInstalledVoices() |
            ForEach-Object {{ $_.VoiceInfo }} |
            Where-Object {{ $_.Culture.Name -like '{culture_prefix}-*' }} |
            Select-Object -First 1

          if ($preferredVoice) {{
            $synth.SelectVoice($preferredVoice.Name)
          }}

          $synth.Rate = {sapi_rate}
          $synth.Volume = 100
          $synth.SetOutputToWaveFile($outputPath)
          $synth.Speak($text)
        }} finally {{
          $synth.Dispose()
        }}
        """
    ).strip()
    return _encode_powershell_command(script)


def _get_temp_output_path(output_path):
    temp_root = Path(os.getenv("TEMP") or os.getenv("TMP") or Path.cwd()) / "wxapp_tts"
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root / output_path.name


def _synthesize_with_windows_voice(text, lang, speed, output_path):
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        raise SpeechSynthesisError("当前环境缺少 PowerShell，无法生成语音文件")

    temp_output_path = _get_temp_output_path(output_path)
    if temp_output_path.exists():
        temp_output_path.unlink(missing_ok=True)

    encoded_command = _build_windows_speech_command(text, lang, speed, temp_output_path)
    completed = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=45,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip() or "系统语音合成失败"
        raise SpeechSynthesisError(message)

    if not temp_output_path.exists() or temp_output_path.stat().st_size <= 0:
        raise SpeechSynthesisError("语音文件生成失败")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(temp_output_path, output_path)
    temp_output_path.unlink(missing_ok=True)


def _ensure_audio_file(text, lang, speed, output_path):
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path, True

    if os.name != "nt":
        raise SpeechSynthesisError("当前部署环境暂不支持离线语音合成")

    try:
        _synthesize_with_windows_voice(text, lang, speed, output_path)
    except Exception:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        raise
    return output_path, False


def build_speech_payload(request, text, lang=DEFAULT_SPEECH_LANG, speed=DEFAULT_SPEECH_SPEED):
    content = _normalize_text(text)
    normalized_lang = _normalize_lang(lang)
    normalized_speed = _normalize_speed(speed)
    output_path = _get_output_path(content, normalized_lang, normalized_speed)
    audio_file, cached = _ensure_audio_file(content, normalized_lang, normalized_speed, output_path)
    relative_path = f"{settings.MEDIA_URL.rstrip('/')}/tts/{audio_file.name}"
    return {
        "audio_url": request.build_absolute_uri(relative_path),
        "content": content,
        "lang": normalized_lang,
        "speed": normalized_speed,
        "provider": "windows_sapi",
        "cached": cached,
    }
