import re

from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String


class greet(Method):
    """Ask Mira to welcome someone and give a short update."""

    def gdo_needs_authentication(self):
        return True

    def gdo_parameters(self):
        return [GDT_String('name').minlen(1).maxlen(64)
                .pattern(r'^[\w][\w.-]{0,63}$').not_null().positional(),
                GDT_String('lang').ascii().minlen(2).maxlen(3).pattern(r'^[a-z]{2,3}$')]

    def gdo_execute(self):
        user = self._env_user
        channel = self._env_channel
        language = self.param_val('lang') or (channel.get_lang_iso() if channel else None) or 'en'
        language = str(language).lower()
        if not re.fullmatch(r'[a-z]{2,3}', language):
            language = 'en'
        args = ('mira.ipc_greet', [str(user.get_id()), self.param_val('name'), language])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('mira_greet_queued')
