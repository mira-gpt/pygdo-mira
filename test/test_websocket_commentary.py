import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gdo.mira.module_mira import module_mira


class WebsocketCommentaryTest(unittest.TestCase):
    def test_only_websocket_commands_when_enabled(self):
        server = MagicMock()
        server.gdo_val.return_value = 'websocket'
        message = SimpleNamespace(_env_server=server, _message='$ping', get_trigger=lambda: '$')
        module = MagicMock()
        with patch('gdo.websocket.module_websocket.module_websocket.instance', return_value=module):
            module.cfg_mira_comment_commands.return_value = False
            self.assertFalse(module_mira.websocket_commentary_requested(message))
            module.cfg_mira_comment_commands.return_value = True
            self.assertTrue(module_mira.websocket_commentary_requested(message))
            message._message = 'hello'
            self.assertFalse(module_mira.websocket_commentary_requested(message))
            message._message = '$'
            self.assertFalse(module_mira.websocket_commentary_requested(message))
            message._message = '$ping'
            server.gdo_val.return_value = 'irc'
            self.assertFalse(module_mira.websocket_commentary_requested(message))


class WebsocketEventTest(unittest.IsolatedAsyncioTestCase):
    async def test_registered_game_host_is_forwarded_without_address(self):
        server = MagicMock()
        server.gdo_val.return_value = 'irc'
        server.get_name.return_value = 'irc'
        author = MagicMock()
        author.get_name.return_value = 'GameBot'
        author.get_server.return_value.get_name.return_value = 'irc'
        message = SimpleNamespace(_env_server=server, _env_channel=None,
                                  _env_user=author, _message='Your turn',
                                  get_trigger=lambda: '$')
        mira = module_mira()
        loader = MagicMock()
        loader.get_module.return_value.is_enabled.return_value = True
        loader.get_module.return_value.is_game_host.return_value = True
        with patch('gdo.mira.module_mira.Application.LOADER', loader, create=True), \
             patch.object(mira, 'is_user_enabled', return_value=True), \
             patch.object(mira, 'is_mirrored_inbound', return_value=False), \
             patch.object(mira, 'websocket_commentary_requested', return_value=False), \
             patch.object(mira, 'is_shadowlamb_reply', return_value=False), \
             patch.object(mira, 'is_addressed', return_value=False), \
             patch.object(mira, 'read_context', return_value='GameBot: Your turn'), \
             patch.object(mira, 'microphone_language', return_value='en'), \
             patch.object(mira, 'with_liveshow_state', side_effect=lambda event: event), \
             patch('gdo.mira.module_mira.Application.temp_path', return_value='/tmp/'), \
             patch('gdo.mira.module_mira.Files.create_dir'), \
             patch('gdo.mira.module_mira.Files.append_content'), \
             patch('gdo.mira.module_mira.Files.remove'), \
             patch('gdo.mira.module_mira.send_to_mira') as send:
            await mira.on_message(message)
        send.assert_called_once()
        self.assertIn('Your turn', send.call_args.args[0])

    async def test_command_is_forwarded_without_modifying_input(self):
        server = MagicMock()
        server.gdo_val.return_value = 'websocket'
        server.get_name.return_value = 'ws'
        author = MagicMock()
        author.get_name.return_value = 'gizmore'
        author.get_server.return_value.get_name.return_value = 'ws'
        message = SimpleNamespace(_env_server=server, _env_channel=None,
                                  _env_user=author, _message='$ping',
                                  get_trigger=lambda: '$')
        mira = module_mira()
        with patch.object(mira, 'is_user_enabled', return_value=True), \
             patch.object(mira, 'is_mirrored_inbound', return_value=False), \
             patch.object(mira, 'websocket_commentary_requested', return_value=True), \
             patch.object(mira, 'is_shadowlamb_reply', return_value=False), \
             patch.object(mira, 'is_addressed', return_value=False), \
             patch.object(mira, 'read_context', return_value='record: $ping'), \
             patch.object(mira, 'microphone_language', return_value='en'), \
             patch.object(mira, 'with_liveshow_state', side_effect=lambda event: event), \
             patch('gdo.mira.module_mira.Application.temp_path', return_value='/tmp/'), \
             patch('gdo.mira.module_mira.Files.create_dir'), \
             patch('gdo.mira.module_mira.Files.append_content'), \
             patch('gdo.mira.module_mira.Files.remove'), \
             patch('gdo.mira.module_mira.send_to_mira') as send:
            await mira.on_message(message)
        self.assertEqual('$ping', message._message)
        self.assertIn('--comment-command=1', send.call_args.args[0])
        self.assertIn('record: $ping', send.call_args.args[0])
