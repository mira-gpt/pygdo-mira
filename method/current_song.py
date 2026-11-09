"""Show current playback metadata from the configured desktop session."""
import asyncio

from gdo.base.Method import Method
from gdo.mira.CurrentSong import desktop_user, read_playing
from gdo.mira.module_mira import module_mira


class current_song(Method):
    @classmethod
    def gdo_trig(cls):
        return 'np'

    async def gdo_execute(self):
        try:
            monitor = getattr(module_mira.instance(), 'current_song_monitor', None)
            preferred = monitor.current[0] if monitor and monitor.current else None
            song = await read_playing(desktop_user(), preferred)
        except (ImportError, OSError, KeyError, ValueError, RuntimeError, asyncio.TimeoutError):
            return self.reply('mira_current_song_unavailable')
        if not song:
            return self.reply('mira_current_song_none')
        return self.reply('mira_current_song_playing', (song[1], song[2]))
