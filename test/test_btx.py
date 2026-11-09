import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.mira.method.btx import btx
from gdo.video.StarWarsIPC import decode_text


class BtxTest(unittest.TestCase):
    def test_short_trigger(self):
        self.assertEqual('btx', btx.gdo_trig())

    def setUp(self):
        Application.mode(Mode.render_cli)

    def method(self):
        method = btx()
        method.param_val = MagicMock(side_effect=lambda key, *args: 'hello' if key == 'text' else None)
        method._env_user = MagicMock()
        method._env_user.get_name.return_value = 'testuser'
        method._env_user.is_authenticated.return_value = True
        method._env_user.is_persisted.return_value = True
        method.has_price_permission = MagicMock(return_value=True)
        method.reply = MagicMock()
        return method

    def test_price_and_queued_text(self):
        method = self.method()
        module = MagicMock()
        module.get_config_val.return_value = '0.10'
        with patch('gdo.mira.method.btx.module_mira.instance', return_value=module), \
                patch('gdo.mira.method.btx.queue_ticker') as send:
            self.assertEqual(1, method.gdo_method_price())
            method.gdo_execute()
        send.assert_called_once_with('testuser: hello')
        method.reply.assert_called_once_with('mira_btx_queued', ('1',))

    def test_denied_balance_never_queues(self):
        method = self.method()
        method.has_price_permission.return_value = False
        with patch('gdo.mira.method.btx.module_mira.instance') as module, \
                patch('gdo.mira.method.btx.queue_ticker') as send:
            module.return_value.get_config_val.return_value = '1.00'
            method.gdo_execute()
        send.assert_not_called()

    def test_unauthenticated_never_queues(self):
        method = self.method()
        method._env_user.is_authenticated.return_value = False
        method.err = MagicMock()
        with patch('gdo.mira.method.btx.queue_ticker') as send:
            method.gdo_execute()
        send.assert_not_called()
        method.err.assert_called_once_with('mira_btx_auth')
