"""Read MPRIS metadata from the configured local desktop session, never control it."""
import asyncio
import json
import pwd
import re

PREFIX = 'org.mpris.MediaPlayer2.'
PATH = '/org/mpris/MediaPlayer2'
PLAYER = 'org.mpris.MediaPlayer2.Player'
UNKNOWN_ARTIST = 'The real Various Artists'


def clean(value, limit=180):
    if not isinstance(value, str):
        return ''
    # Some ICY streams expose UTF-8 bytes decoded as Latin-1 over MPRIS.
    if any(marker in value for marker in ('Ã', 'Â', 'â€')):
        try:
            value = value.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return ' '.join(''.join(c if c.isprintable() else ' ' for c in value).split())[:limit]


def song_from_metadata(metadata):
    def value(key):
        item = metadata.get(key, {})
        return item.get('data') if isinstance(item, dict) else None

    title = clean(value('xesam:title'))
    artists = value('xesam:artist')
    artist = clean(', '.join(a for a in artists if isinstance(a, str))) if isinstance(artists, list) else clean(artists)
    icy = clean(value('icy-title'))
    if not title and icy:
        parts = icy.split(' - ', 1)
        if len(parts) == 2:
            artist, title = clean(parts[0]), clean(parts[1])
        else:
            title = icy
    if not title:
        return None
    if not artist or artist.casefold() in ('unknown', 'unknown artist'):
        artist = UNKNOWN_ARTIST
    return artist, title


async def busctl(session_user, *args):
    from gdo.audio.session import audio_session_command
    command = ['busctl', '--user', '--json=short', *args]
    if session_user:
        account = pwd.getpwnam(session_user)
        command = ['env', f'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{account.pw_uid}/bus', *command]
    command = audio_session_command(command, session_user)
    process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.DEVNULL)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 3)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        process.kill()
        await process.wait()
        raise
    if process.returncode or len(output) > 1048576:
        raise RuntimeError('Cannot query the desktop media session')
    return output.decode('utf-8')


async def read_playing(session_user=None, preferred=None):
    entries = json.loads(await busctl(session_user, 'list'))
    names = sorted({entry['name'] for entry in entries if isinstance(entry, dict)
                    and isinstance(entry.get('name'), str) and entry['name'].startswith(PREFIX)
                    and re.fullmatch(r'[A-Za-z0-9_.-]+', entry['name'])})[:16]
    if preferred in names:
        names.remove(preferred)
        names.insert(0, preferred)
    for name in names:
        try:
            output = await busctl(session_user, 'get-property', name, PATH, PLAYER, 'PlaybackStatus', 'Metadata')
            rows = [json.loads(line) for line in output.splitlines() if line.strip()]
            if len(rows) != 2 or rows[0].get('data') != 'Playing':
                continue
            song = song_from_metadata(rows[1].get('data', {}))
            if song:
                return name, *song
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, asyncio.TimeoutError):
            continue
    return None


def desktop_user():
    try:
        from gdo.audio.module_audio import module_audio
        module = module_audio.instance()
        return module.get_config_val('audio_output_session_user') or None if module else None
    except (ImportError, AttributeError):
        return None


class CurrentSongMonitor:
    def __init__(self):
        self.current = None
        self.last_queued = None
        self.busy = False

    async def poll(self):
        if self.busy:
            return
        self.busy = True
        try:
            preferred = self.current[0] if self.current else None
            self.current = await read_playing(desktop_user(), preferred)
            if self.current and self.current[1:] != self.last_queued:
                from gdo.video.MicTicker import MicTicker
                artist, title = self.current[1:]
                MicTicker.enqueue(f'Now playing: {artist} - {title}'[:300])
                self.last_queued = (artist, title)
        finally:
            self.busy = False
