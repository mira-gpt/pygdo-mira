"""Bounded text splitting and in-process assembly for sequential read-aloud."""
import asyncio
import re
from urllib.parse import urlsplit

import httpx

MAX_TEXT = 20000
PART_SIZE = 200
playback_lock = None
tasks = set()


def detect_voice(text, fallback):
    """Conservative local de/en heuristic; uncertain text keeps the user voice."""
    words = re.findall(r"[^\W\d_]+", text.casefold())
    de = {'der', 'die', 'das', 'und', 'ist', 'wir', 'ein', 'eine', 'nicht', 'von', 'mit', 'zu', 'für', 'den', 'unser', 'unsere'}
    en = {'the', 'and', 'is', 'we', 'a', 'an', 'not', 'of', 'with', 'to', 'for', 'our', 'are', 'this', 'that'}
    german = sum(w in de for w in words) + sum(any(c in w for c in 'äöüß') for w in words)
    english = sum(w in en for w in words)
    if german >= 3 and german >= english + 2:
        return 'de'
    if english >= 3 and english >= german + 2:
        return 'en'
    return fallback


def start(coroutine):
    task = asyncio.create_task(coroutine)
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return task


async def stop():
    active = list(tasks)
    for task in active:
        task.cancel()
    if active:
        await asyncio.gather(*active, return_exceptions=True)


async def fetch_text(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use an HTTP or HTTPS URL without credentials')
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        async with client.stream('GET', url) as response:
            if response.is_redirect:
                raise ValueError('Redirects are not supported; use the direct text URL')
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').split(';', 1)[0].lower()
            if content_type and content_type not in ('text/plain', 'text/markdown', 'application/octet-stream'):
                raise ValueError('URL must return plain text, not HTML or a binary document')
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_TEXT * 4:
                    raise ValueError('URL text exceeds the size limit')
    return data.decode('utf-8-sig')


def split_text(text, size=PART_SIZE):
    if len(text) > MAX_TEXT:
        raise ValueError(f'Text must have 1 to {MAX_TEXT} characters')
    # ASCII art and separators should not be spoken as long symbol sequences.
    text = re.sub(r'([^\w\s]|_)\1{2,}', ' ', text)
    text = ' '.join(text.split())
    if not text:
        raise ValueError(f'Text must have 1 to {MAX_TEXT} characters')
    pieces = []
    while len(text) > size:
        cut = text.rfind(' ', 0, size + 1)
        if cut < size // 3:
            cut = size
        pieces.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        pieces.append(text)
    return pieces


async def play(parts, target, voice):
    global playback_lock
    if playback_lock is None:
        playback_lock = asyncio.Lock()
    async with playback_lock:
        from gdo.audio.method.ipc_say import ipc_say
        if target:
            from gdo.translate.GTranslate import GTranslate
            from gdo.translate.module_translate import module_translate
            translator = module_translate.instance()
            key = translator.cfg_google_api_key()
            if not key:
                raise ValueError('Translation module has no configured Google API key')
        for part in parts:
            if target:
                part = (await GTranslate.translate(part, target=target, api_key=key)).text
            for spoken in split_text(part, 300):
                await ipc_say().input('text', spoken).input('lang', voice).gdo_execute()
