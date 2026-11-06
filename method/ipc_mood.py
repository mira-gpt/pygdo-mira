from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.mira.GDT_MiraMood import GDT_MiraMood
from gdo.mira.module_mira import module_mira


class ipc_mood(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_MiraMood('key').not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                await module_mira.instance().save_config_val('mira_mood', self.param_val('key'), force=True)
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Mira mood change failed: {error}')
        return self.empty()
