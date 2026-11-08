import re

from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method


class sup(Method):
    """Ask Mira for a short spoken update."""

    def gdo_needs_authentication(self):
        return True

    def gdo_execute(self):
        user = self._env_user
        language = user.get_lang_iso() or (self._env_channel.get_lang_iso() if self._env_channel else 'en')
        language = str(language).lower()
        if not re.fullmatch(r'[a-z]{2,3}', language):
            language = 'en'
        args = ('mira.ipc_sup', [str(user.get_id()), language])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('mira_sup_queued')
