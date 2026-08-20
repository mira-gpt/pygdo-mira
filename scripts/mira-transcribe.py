#!/home/gizmore/www/pygdo/.venv/bin/python
"""Transcribe bounded clips or run the local ``micro1`` continuous listener.

Even in listener mode audio is processed in short clips. A raw WAV exists only
while that clip is transcribed, then is deleted. The audio trigger forwards
only a transcript line beginning with ``mira``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


MIC_USER = "mira-mic"
DEVICE = "plughw:1,0"
MODEL_CACHE = "/home/mira/.cache/mira-whisper"
QUEUE = Path(__file__).resolve().parents[1] / "inqueue" / "micro1"
SUBMIT_PAUSE_SECONDS = 3.223


def timestamp(at: datetime) -> str:
    return at.strftime("%Y-%m-%d %H:%M:%S.%f")


def sudo_as_mic(*command: str, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sudo", "-n", "-u", MIC_USER, "--", *command],
        text=True,
        check=True,
        **kwargs,
    )


def format_segments(segments, started: datetime) -> str:
    """Turn faster-whisper's timed segments into standard IBDES records.

    Only a 3223 ms gap gets a blank separator. This preserves short natural
    pauses inside one thought and creates a new sendable unit after a real
    break.
    """
    rows: list[str] = []
    previous_end: float | None = None
    for segment in segments:
        text = " ".join(segment.text.split())
        if not text:
            continue
        start = segment.start
        if previous_end is not None and start - previous_end >= SUBMIT_PAUSE_SECONDS:
            rows.append("")
        rows.append(f"{timestamp(started + timedelta(seconds=start))} #- mira-mic{{micro1}} {text}")
        previous_end = segment.end
    return "\n".join(rows) + ("\n" if rows else "")


def queue_payload(ibdes: str) -> Path:
    QUEUE.mkdir(mode=0o770, parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S.%f")
    target = QUEUE / f"{stamp}.json"
    temporary = QUEUE / f".{stamp}.tmp"
    temporary.write_text(json.dumps({"source": "micro1", "ibdes": ibdes}, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return target


def transcribe_clip(model, seconds: int, language: str) -> str:
    """Capture and transcribe exactly one clip; always dispose of raw audio."""
    temporary = Path(tempfile.mkdtemp(prefix="mira-stt-"))
    audio = temporary / "clip.wav"
    try:
        # The capture account alone has access to the physical ALSA device.
        subprocess.run(["sudo", "-n", "chown", f"{MIC_USER}:{MIC_USER}", str(temporary)], check=True)
        started = datetime.now()
        sudo_as_mic(
            "/usr/bin/arecord", "-D", DEVICE, "-f", "S16_LE", "-r", "16000", "-c", "1",
            "-d", str(seconds), str(audio),
        )
        # Only the bounded clip becomes readable by the local transcriber.
        subprocess.run(["sudo", "-n", "chown", "mira:mira", str(temporary)], check=True)
        segments, _info = model.transcribe(str(audio), language=language, vad_filter=True)
        return format_segments(segments, started)
    finally:
        subprocess.run(["sudo", "-n", "rm", "-rf", "--", str(temporary)], check=False)
        shutil.rmtree(temporary, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=8, help="clip length (1..60, default: 8)")
    parser.add_argument("--language", default="de", help="Whisper language code (default: de)")
    parser.add_argument("--listen", action="store_true", help="listen continuously in short local clips")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 60:
        parser.error("--seconds must be between 1 and 60")

    from faster_whisper import WhisperModel
    model = WhisperModel(
        "base", device="cpu", compute_type="int8", download_root=MODEL_CACHE,
        local_files_only=True,
    )
    try:
        while True:
            ibdes = transcribe_clip(model, args.seconds, args.language)
            if ibdes:
                target = queue_payload(ibdes)
                print(ibdes, end="")
                print(f"Queued: {target}", flush=True)
            else:
                print("No speech transcribed.", flush=True)
            if not args.listen:
                return 0
    except KeyboardInterrupt:
        print("micro1 listener stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
