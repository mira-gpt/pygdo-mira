from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.core.GDT_UInt import GDT_UInt
from gdo.mira.module_mira import module_mira
from gdo.mira.util import send_to_mira


class ipc_sup(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_UInt('user').min(1).not_null().positional(),
                GDT_String('lang').ascii().minlen(2).maxlen(3).pattern(r'^[a-z]{2,3}$').not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            mode = module_mira.instance().cfg_mira_livemode()
            send_to_mira(f'$chatsup --live={mode} --user={self.param_val("user")} --lang={self.param_val("lang")}',
                         interrupt=False)
        return self.empty()
