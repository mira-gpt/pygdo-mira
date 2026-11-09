import unittest
from unittest.mock import patch

from gdo.mira.module_mira import module_mira


class AudioChatStreamTest(unittest.IsolatedAsyncioTestCase):
    async def test_microphone_event_uses_agent_bridge_without_interrupt(self):
        event = '$chatstream 12 --lang=en --call=mic --seq=0 --status=final --user=42\nHello'
        with patch('gdo.mira.module_mira.send_to_mira') as send, \
                patch.object(module_mira, 'cfg_mira_livemode', return_value='discuss'):
            await module_mira().on_audio_chatstream(event)
        send.assert_called_once_with(event.replace('\n', ' --live=discuss\n', 1), interrupt=False)

    def test_state_reports_off_and_unknown(self):
        mira = module_mira()
        event = '$chat --lang=en\nhello\n$chat_done'
        with patch.object(mira, 'cfg_mira_livemode', return_value='off'):
            self.assertEqual('$chat --lang=en --live=off\nhello\n$chat_done', mira.with_liveshow_state(event))
        with patch.object(mira, 'cfg_mira_livemode', side_effect=RuntimeError('unavailable')):
            self.assertIn('--live=unknown', mira.with_liveshow_state(event))

    def test_legacy_setting_and_explicit_modes(self):
        mira = module_mira()
        with patch.object(mira, 'get_config_val', return_value=None), patch.object(mira, 'get_config_value', return_value=True):
            self.assertEqual('show', mira.cfg_mira_livemode())
        with patch.object(mira, 'get_config_val', return_value=None), patch.object(mira, 'get_config_value', return_value=False):
            self.assertEqual('off', mira.cfg_mira_livemode())
        for mode in ('off', 'work', 'show', 'discuss', 'cohost'):
            with patch.object(mira, 'get_config_val', return_value=mode):
                self.assertEqual(mode, mira.cfg_mira_livemode())

    async def test_cohost_is_forwarded_to_agent(self):
        event = '$chatstream 12 --lang=en --call=mic --seq=0 --status=final --user=42\nHello'
        with patch('gdo.mira.module_mira.send_to_mira') as send, \
                patch.object(module_mira, 'cfg_mira_livemode', return_value='cohost'):
            await module_mira().on_audio_chatstream(event)
        send.assert_called_once_with(event.replace('\n', ' --live=cohost\n', 1), interrupt=False)
