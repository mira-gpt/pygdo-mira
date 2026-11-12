"""Append visible Codex conversation messages from one JSONL session to a private log."""
import json
import os
import sys
import time

MAX_LINE = 1024 * 1024


def conversation_entry(line):
    try:
        event = json.loads(line)
        payload = event.get('payload', {})
        if event.get('type') != 'response_item' or payload.get('type') != 'message':
            return None
        role = payload.get('role')
        if role == 'user':
            kind = 'input_text'
        elif role == 'assistant' and payload.get('phase') in ('commentary', 'final_answer'):
            kind = 'output_text'
        else:
            return None
        content = payload.get('content')
        if not isinstance(content, list):
            return None
        parts = [p['text'] for p in content if isinstance(p, dict) and p.get('type') == kind and isinstance(p.get('text'), str)]
        text = '\n'.join(parts).strip()
        if not text:
            return None
        return {'timestamp': event.get('timestamp'), 'role': role, 'text': text}
    except (ValueError, TypeError, AttributeError):
        return None


def format_entry(entry):
    timestamp = entry.get('timestamp') or 'unknown time'
    role = 'Mira' if entry.get('role') == 'assistant' else 'Input'
    return f'[{timestamp}] {role}:\n{entry["text"]}\n\n'


def follow(source, destination):
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(destination, flags, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'a', encoding='utf-8', buffering=1) as out:
        while True:
            try:
                with open(source, 'rb') as stream:
                    stream.seek(0, os.SEEK_END)
                    pending, oversized = b'', False
                    while True:
                        chunk = stream.read(65536)
                        if not chunk:
                            current = os.stat(source)
                            if current.st_ino != os.fstat(stream.fileno()).st_ino or current.st_size < stream.tell():
                                break
                            time.sleep(.25)
                            continue
                        for part in chunk.splitlines(keepends=True):
                            if not oversized:
                                pending += part
                                if len(pending) > MAX_LINE:
                                    pending, oversized = b'', True
                            if part.endswith(b'\n'):
                                entry = None if oversized else conversation_entry(pending)
                                if entry:
                                    out.write(format_entry(entry))
                                pending, oversized = b'', False
            except OSError as error:
                print(f'Compact log source unavailable: {type(error).__name__}', file=sys.stderr, flush=True)
                time.sleep(2)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: CompactLog.py SESSION.jsonl OUTPUT.log')
    follow(sys.argv[1], sys.argv[2])
