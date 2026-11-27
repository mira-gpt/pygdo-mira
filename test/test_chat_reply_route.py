from types import SimpleNamespace
from unittest.mock import patch

from gdo.mira.module_mira import module_mira
from gdotest.TestUtil import GDOTestCase


class ChatReplyRouteTest(GDOTestCase):
    def test_channel_and_private_routes(self):
        channel = SimpleNamespace(get_id=lambda: '240', get_lang_iso=lambda: 'en', get_trigger=lambda: '.')
        sender = SimpleNamespace(get_id=lambda: '17')
        with patch.object(module_mira, 'microphone_language', return_value='en'):
            self.assertIn('$chat --reply-in=240 ', module_mira.chat_event(channel, 'hello', sender))
            self.assertIn('$chat --reply-to=17 ', module_mira.chat_event(None, 'hello', sender))
            self.assertNotIn('--reply-', module_mira.chat_event(None, 'hello'))

    def test_invalid_ids_do_not_inject_headers(self):
        for value in ('0', '-1', '12\n$chat_done', '1 --reply-to=2'):
            sender = SimpleNamespace(get_id=lambda: value)
            self.assertNotIn('--reply-', module_mira.chat_event(None, 'hello', sender))
