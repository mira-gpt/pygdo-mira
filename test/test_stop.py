import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.mira.method.ipc_stop import ipc_stop
from gdo.mira.method.stop import stop


class StopTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_public_stop_is_owner_only_and_queues_ipc(self):
        command = stop()
        self.assertEqual('owner', command.gdo_user_permission())
        command.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'IS_DOG', False), patch.object(Application, 'db', return_value=db), \
                patch('gdo.mira.method.stop.IPC.send_to_dog') as send:
            self.assertEqual('queued', command.gdo_execute())
        send.assert_called_once_with('mira.ipc_stop', [])

    async def test_dog_stops_playback_and_presentation(self):
        handler = ipc_stop()
        handler.empty = MagicMock()
        mira = MagicMock()
        mira._away_task = None
        video = MagicMock()
        audio_module = MagicMock()
        audio_module.save_config_val = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.audio.PlaybackTasks.PlaybackTasks.stop', new_callable=AsyncMock) as audio, \
                patch('gdo.audio.module_audio.module_audio.instance', return_value=audio_module), \
                patch('gdo.mira.ReadAlong.stop', new_callable=AsyncMock) as readalong, \
                patch('gdo.mira.module_mira.module_mira.instance', return_value=mira), \
                patch('gdo.video.module_video.module_video.instance', return_value=video):
            await handler.gdo_execute()
        audio.assert_awaited_once()
        audio_module.save_config_val.assert_awaited_once_with('audio_microphone', '0')
        readalong.assert_awaited_once()
        video.connector.close_effects.assert_called_once_with('presentation')
