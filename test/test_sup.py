import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.mira.method.sup import sup
from gdo.mira.method.ipc_sup import ipc_sup


class SupTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_request_queues_user_and_language(self):
        method = sup()
        method._env_user = MagicMock(get_lang_iso=MagicMock(return_value='de'), get_id=MagicMock(return_value=1))
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.mira.method.sup.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('mira.ipc_sup', ['1', 'de'])
        self.assertTrue(method.gdo_needs_authentication())

    def test_request_defers_until_transaction_commits(self):
        method = sup()
        method._env_user = MagicMock(get_lang_iso=MagicMock(return_value=''), get_id=MagicMock(return_value=7))
        method._env_channel = MagicMock(get_lang_iso=MagicMock(return_value='ko'))
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = True
        with patch.object(Application, 'db', return_value=db), patch.object(Application, 'defer_after_commit') as defer, \
                patch('gdo.mira.method.sup.IPC.send_to_dog') as send:
            method.gdo_execute()
        defer.assert_called_once_with(send, 'mira.ipc_sup', ['7', 'ko'])
        send.assert_not_called()

    def test_dog_delivers_current_mode_without_interrupting(self):
        method = ipc_sup()
        method.param_val = MagicMock(side_effect=lambda key: {'user': '1', 'lang': 'de'}[key])
        method.empty = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.mira.method.ipc_sup.module_mira.instance') as instance, \
                patch('gdo.mira.method.ipc_sup.send_to_mira') as send:
            instance.return_value.cfg_mira_livemode.return_value = 'discuss'
            method.gdo_execute()
        send.assert_called_once_with('$chatsup --live=discuss --user=1 --lang=de', interrupt=False)

    def test_non_dog_does_not_deliver(self):
        method = ipc_sup()
        method.empty = MagicMock()
        with patch.object(Application, 'IS_DOG', False), patch('gdo.mira.method.ipc_sup.send_to_mira') as send:
            method.gdo_execute()
        send.assert_not_called()
