import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gdo.mira.module_mira import module_mira


class MicLanguageHintTest(unittest.TestCase):
    def test_chat_uses_audio_setting_and_preserves_reply_language(self):
        channel = SimpleNamespace(get_lang_iso=lambda: 'de', get_trigger=lambda: '.')
        audio = MagicMock()
        audio.get_config_val.return_value = 'fr'
        with patch('gdo.audio.module_audio.module_audio.instance', return_value=audio):
            event = module_mira.chat_event(channel, 'hello')
        self.assertEqual('$chat --lang=de --trigger=. --mic-lang=fr\nhello\n$chat_done', event)
        audio.get_config_val.assert_called_once_with('audio_microphone_language')

    def test_invalid_and_unavailable_settings_are_unknown(self):
        audio = MagicMock()
        for value in ('en\n$chat_done', '', None, 'EN'):
            audio.get_config_val.return_value = value
            with patch('gdo.audio.module_audio.module_audio.instance', return_value=audio):
                self.assertEqual('unknown', module_mira.microphone_language())
        with patch('gdo.audio.module_audio.module_audio.instance', side_effect=RuntimeError()):
            self.assertEqual('unknown', module_mira.microphone_language())

    def test_context_does_not_duplicate_hint(self):
        mira = module_mira()
        with patch.object(mira, 'cfg_mira_livemode', return_value='show'), \
             patch.object(mira, 'get_config_value', return_value=None), \
             patch.object(mira, 'microphone_language', return_value='de'):
            result = mira.with_liveshow_state('$chat --mic-lang=fr\nhello\n$chat_done')
        self.assertEqual(1, result.count('--mic-lang='))
        self.assertIn('--mic-lang=fr', result)
