import unittest
from unittest.mock import patch

from gdo.mira.module_mira import module_mira


class AudioChatStreamTest(unittest.IsolatedAsyncioTestCase):
    async def test_microphone_event_uses_agent_bridge_without_interrupt(self):
        event = '$chatstream 12 --lang=en --call=mic --seq=0 --status=final --user=42\nHello'
        with patch('gdo.mira.module_mira.send_to_mira') as send:
            await module_mira().on_audio_chatstream(event)
        send.assert_called_once_with(event, interrupt=False)
