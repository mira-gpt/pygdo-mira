from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.core.GDT_UInt import GDT_UInt
from gdo.mira.module_mira import module_mira
from gdo.mira.util import send_to_mira


class ipc_greet(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_UInt('user').min(1).not_null().positional(),
                GDT_String('name').minlen(1).maxlen(64)
                .pattern(r'^[\w][\w.-]{0,63}$').not_null().positional(),
                GDT_String('lang').ascii().minlen(2).maxlen(3)
                .pattern(r'^[a-z]{2,3}$').not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            event = (f'$chatgreet --user={self.param_val("user")} '
                     f'--name={self.param_val("name")} --lang={self.param_val("lang")}')
            send_to_mira(module_mira.instance().with_liveshow_state(event), interrupt=False)
        return self.empty()
