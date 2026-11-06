#!/home/gizmore/www/pygdo/.venv/bin/python
"""Stream short local microphone transcripts to Mira until interrupted."""
import argparse
import queue
import signal
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np
import whisper

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from gdo.mira.util import send_to_mira

RATE = 16000
CHUNK_SECONDS = 4


def has_voice(samples: np.ndarray, threshold: float = 0.008) -> bool:
    return bool(samples.size and np.sqrt(np.mean(samples * samples)) >= threshold)


def read_chunks(stream, pending: queue.Queue, stopped: threading.Event):
    size = RATE * CHUNK_SECONDS * 2
    while not stopped.is_set():
        data = bytearray()
        while len(data) < size and not stopped.is_set():
            block = stream.read(size - len(data))
            if not block:
                stopped.set()
                break
            data.extend(block)
        if len(data) != size:
            break
        samples = np.frombuffer(data, dtype='<i2').astype(np.float32) / 32768.0
        if has_voice(samples):
            try:
                pending.put_nowait(samples)
            except queue.Full:
                print('Microphone: transcription is behind; a chunk was dropped.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='PulseAudio microphone source name')
    args = parser.parse_args()
    def stop(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    model_file = Path('/home/mira/.cache/whisper/base.pt')
    if not model_file.is_file():
        raise SystemExit('Local Whisper model is missing; no download was attempted.')
    model = whisper.load_model(str(model_file), device='cpu')
    command = ['sudo', '-n', '-u', 'gizmore', 'env', 'XDG_RUNTIME_DIR=/run/user/1000',
               'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
               '-f', 'pulse', '-i', args.source, '-ac', '1', '-ar', str(RATE),
               '-f', 's16le', 'pipe:1']
    capture = subprocess.Popen(command, stdout=subprocess.PIPE)
    stopped = threading.Event()
    pending = queue.Queue(maxsize=2)
    reader = threading.Thread(target=read_chunks, args=(capture.stdout, pending, stopped), daemon=True)
    reader.start()
    print('Microphone listener active; local transcription, no audio files.', flush=True)
    try:
        while not stopped.is_set() or not pending.empty():
            try:
                samples = pending.get(timeout=0.5)
            except queue.Empty:
                continue
            result = model.transcribe(samples, fp16=False, verbose=False, condition_on_previous_text=False)
            text = str(result.get('text', '')).strip()
            if text:
                send_to_mira(f'[Microphone transcript] {text}', interrupt=False)
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        capture.terminate()
        capture.wait(timeout=5)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
