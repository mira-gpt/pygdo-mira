import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.core.GDO_Permission import GDO_Permission
from gdo.core.GDT_User import GDT_User
from gdo.mira.method.host import host


class HostTest(unittest.IsolatedAsyncioTestCase):
    async def test_admin_sets_user_id(self):
        method = host.__new__(host)
        user = MagicMock()
        user.get_id.return_value = '42'
        user.get_name.return_value = 'Giz'
        method.param_value = MagicMock(return_value=user)
        method.reply = MagicMock(return_value='ok')
        with patch('gdo.mira.method.host.module_mira.instance') as instance:
            instance.return_value.save_config_val = AsyncMock()
            self.assertEqual('ok', await method.gdo_execute())
        self.assertEqual(GDO_Permission.ADMIN, method.gdo_user_permission())
        instance.return_value.save_config_val.assert_awaited_once_with('mira_show_host', '42')
        method.reply.assert_called_once_with('msg_mira_show_host', ('Giz',))

    def test_parameter_is_user(self):
        with patch('gdo.base.Application.Application.get_mode', return_value=None), \
             patch('gdo.core.GDO_User.GDO_User.table'):
            self.assertIsInstance(host.__new__(host).gdo_parameters()[0], GDT_User)
