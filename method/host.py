from gdo.base.Method import Method
from gdo.core.GDO_Permission import GDO_Permission
from gdo.core.GDT_User import GDT_User
from gdo.mira.module_mira import module_mira


class host(Method):
    @classmethod
    def gdo_trigger(cls):
        return 'mira.host'

    def gdo_user_permission(self):
        return GDO_Permission.ADMIN

    def gdo_parameters(self):
        return [GDT_User('user').not_null().positional()]

    async def gdo_execute(self):
        user = self.param_value('user')
        await module_mira.instance().save_config_val('mira_show_host', user.get_id())
        return self.reply('msg_mira_show_host', (user.get_name(),))
