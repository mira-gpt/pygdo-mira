"""Request a stop of Mira-owned playback and presentation effects."""
from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method


class stop(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_execute(self):
        args = ('mira.ipc_stop', [])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.empty() if Application.IS_DOG else self.reply('mira_stop_queued')
