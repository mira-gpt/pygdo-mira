import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.mira.method.greet import greet
from gdo.mira.method.ipc_greet import ipc_greet


class GreetTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_channel_language_and_name(self):
        method = greet()
        method._env_user = MagicMock(get_id=MagicMock(return_value=1))
        method._env_channel = MagicMock(get_lang_iso=MagicMock(return_value='de'))
        method.param_val = MagicMock(side_effect=lambda k: {'name': 'Pawel', 'lang': None}[k])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.mira.method.greet.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('mira.ipc_greet', ['1', 'Pawel', 'de'])
        self.assertTrue(method.gdo_needs_authentication())

    def test_override_and_transaction(self):
        method = greet()
        method._env_user = MagicMock(get_id=MagicMock(return_value=7))
        method._env_channel = MagicMock(get_lang_iso=MagicMock(return_value='de'))
        method.param_val = MagicMock(side_effect=lambda k: {'name': 'Pawel', 'lang': 'ko'}[k])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = True
        with patch.object(Application, 'db', return_value=db), patch.object(Application, 'defer_after_commit') as defer, \
                patch('gdo.mira.method.greet.IPC.send_to_dog') as send:
            method.gdo_execute()
        defer.assert_called_once_with(send, 'mira.ipc_greet', ['7', 'Pawel', 'ko'])
        send.assert_not_called()

    def test_missing_channel_defaults_to_english(self):
        method = greet()
        method._env_user = MagicMock(get_id=MagicMock(return_value=2))
        method._env_channel = None
        method.param_val = MagicMock(side_effect=lambda k: {'name': 'Pawel', 'lang': None}[k])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.mira.method.greet.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('mira.ipc_greet', ['2', 'Pawel', 'en'])

    def test_event_and_non_dog(self):
        method = ipc_greet()
        method.param_val = MagicMock(side_effect=lambda k: {'user': '7', 'name': 'Pawel', 'lang': 'ko'}[k])
        method.empty = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.mira.method.ipc_greet.module_mira.instance') as instance, \
                patch('gdo.mira.method.ipc_greet.send_to_mira') as send:
            instance.return_value.cfg_mira_livemode.return_value = 'show'
            method.gdo_execute()
        send.assert_called_once_with('$chatgreet --live=show --user=7 --name=Pawel --lang=ko', interrupt=False)
        with patch.object(Application, 'IS_DOG', False), patch('gdo.mira.method.ipc_greet.send_to_mira') as send:
            method.gdo_execute()
        send.assert_not_called()

    def test_parameter_definitions_construct(self):
        self.assertEqual(len(greet().gdo_parameters()), 2)
        self.assertEqual(len(ipc_greet().gdo_parameters()), 3)
