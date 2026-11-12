import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.mira.CurrentSong import CurrentSongMonitor, UNKNOWN_ARTIST, read_playing, song_from_metadata


def field(data):
    return {'data': data}


class SongMetadataTest(unittest.TestCase):
    def test_now_playing_trigger(self):
        from gdo.mira.method.current_song import current_song
        self.assertEqual('np', current_song.gdo_trig())

    def test_standard_and_stream_metadata(self):
        self.assertEqual(('Artist', 'Title'), song_from_metadata({'xesam:artist': field(['Artist']), 'xesam:title': field('Title')}))
        self.assertEqual(('Remixer', 'Radio track'), song_from_metadata({'icy-title': field('Remixer - Radio track')}))
        self.assertEqual(('Bachliñski', 'Song'), song_from_metadata({'icy-title': field('BachliÃ±ski - Song')}))
        self.assertEqual((UNKNOWN_ARTIST, 'Solo'), song_from_metadata({'xesam:title': field('Solo')}))
        self.assertEqual(('Various Artists', 'Compilation'), song_from_metadata({'xesam:artist': field(['Various Artists']), 'xesam:title': field('Compilation')}))
        self.assertIsNone(song_from_metadata({}))

    def test_metadata_is_single_line(self):
        self.assertEqual(('A B', 'C D'), song_from_metadata({'xesam:artist': field(['A\nB']), 'xesam:title': field('C\x00D')}))


class SongMonitorTest(unittest.IsolatedAsyncioTestCase):
    async def test_song_change_emits_only_once(self):
        from gdo.base.Application import Application
        events = MagicMock()
        events.publish = AsyncMock()
        monitor = CurrentSongMonitor()
        with patch.object(Application, 'EVENTS', events, create=True), \
                patch('gdo.mira.CurrentSong.desktop_user', return_value=None), \
                patch('gdo.mira.CurrentSong.read_playing_all', new_callable=AsyncMock,
                      return_value=[('player', 'Artist', 'Song')]), \
                patch('gdo.video.MicTicker.MicTicker.enqueue'):
            await monitor.poll()
            await monitor.poll()
        events.publish.assert_awaited_once_with('mira_current_song_changed', 'Artist', 'Song')

    async def test_cohost_monitors_song_changes(self):
        from gdo.base.Application import Application
        from gdo.mira.module_mira import module_mira
        module = module_mira()
        module.current_song_monitor = MagicMock()
        module.current_song_monitor.poll = AsyncMock()
        module.cfg_mira_livemode = MagicMock(return_value='cohost')
        module.get_config_val = MagicMock(return_value='1')
        with patch.object(Application, 'IS_DOG', True):
            await module.current_song_timer()
            module.get_config_val.return_value = '0'
            await module.current_song_timer()
        module.current_song_monitor.poll.assert_awaited_once()

    async def test_leaving_show_forgets_tracks_so_return_announces_current_song(self):
        from gdo.base.Application import Application
        from gdo.mira.module_mira import module_mira
        module = module_mira()
        module.current_song_monitor = CurrentSongMonitor()
        module.current_song_monitor.player_tracks = {'player': ('artist', 'song')}
        module.cfg_mira_livemode = MagicMock(return_value='discuss')
        with patch.object(Application, 'IS_DOG', True):
            await module.current_song_timer()
        self.assertEqual({}, module.current_song_monitor.player_tracks)

    async def test_timer_only_runs_in_show_mode_and_when_enabled(self):
        from gdo.base.Application import Application
        from gdo.mira.module_mira import module_mira
        module = module_mira()
        module.current_song_monitor = MagicMock()
        module.current_song_monitor.poll = AsyncMock()
        module.cfg_mira_livemode = MagicMock(return_value='off')
        module.get_config_val = MagicMock(return_value='1')
        with patch.object(Application, 'IS_DOG', True):
            await module.current_song_timer()
            module.cfg_mira_livemode.return_value = 'show'
            module.get_config_val.return_value = '0'
            await module.current_song_timer()
            module.get_config_val.return_value = '1'
            await module.current_song_timer()
        module.current_song_monitor.poll.assert_awaited_once()

    async def test_only_playing_player_and_preferred_player(self):
        players = json.dumps([{'name': 'org.mpris.MediaPlayer2.firefox'}, {'name': 'org.mpris.MediaPlayer2.celluloid'}])
        playing = '\n'.join([json.dumps(field('Playing')), json.dumps(field({'xesam:title': field('Song')}))])
        paused = '\n'.join([json.dumps(field('Paused')), json.dumps(field({}))])
        with patch('gdo.mira.CurrentSong.busctl', new_callable=AsyncMock, side_effect=[players, playing, paused]) as bus:
            self.assertEqual(('org.mpris.MediaPlayer2.firefox', UNKNOWN_ARTIST, 'Song'),
                             await read_playing('user', 'org.mpris.MediaPlayer2.firefox'))
        self.assertIn('org.mpris.MediaPlayer2.firefox', bus.await_args_list[1].args)

    async def test_paused_player_is_ignored(self):
        players = json.dumps([{'name': 'org.mpris.MediaPlayer2.firefox'}])
        paused = '\n'.join([json.dumps(field('Paused')), json.dumps(field({'xesam:title': field('Song')}))])
        with patch('gdo.mira.CurrentSong.busctl', new_callable=AsyncMock, side_effect=[players, paused]):
            self.assertIsNone(await read_playing())

    async def test_changes_only_and_retry_on_full_queue(self):
        monitor = CurrentSongMonitor()
        song = ('player', 'Artist', 'Song')
        with patch('gdo.mira.CurrentSong.desktop_user', return_value=None), \
                patch('gdo.mira.CurrentSong.read_playing_all', new_callable=AsyncMock, return_value=[song]), \
                patch('gdo.video.MicTicker.MicTicker.enqueue', side_effect=[ValueError('full'), None]) as enqueue:
            with self.assertRaises(ValueError):
                await monitor.poll()
            await monitor.poll()
            await monitor.poll()
        self.assertEqual(2, enqueue.call_count)
        enqueue.assert_called_with('Now playing: Artist - Song')

    async def test_firefox_track_is_queued_while_radio_keeps_playing(self):
        monitor = CurrentSongMonitor()
        radio = ('org.mpris.MediaPlayer2.celluloid', 'Station', 'Radio')
        firefox = ('org.mpris.MediaPlayer2.firefox.instance1', 'Artist', 'YouTube song')
        with patch('gdo.mira.CurrentSong.desktop_user', return_value=None), \
                patch('gdo.mira.CurrentSong.read_playing_all', new_callable=AsyncMock,
                      side_effect=[[radio], [radio, firefox], [radio, firefox]]), \
                patch('gdo.video.MicTicker.MicTicker.enqueue') as enqueue:
            await monitor.poll()
            await monitor.poll()
            await monitor.poll()
        self.assertEqual(2, enqueue.call_count)
        enqueue.assert_called_with('Now playing: Artist - YouTube song')
