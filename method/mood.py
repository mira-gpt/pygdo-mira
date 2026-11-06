from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.mira.GDT_MiraMood import GDT_MiraMood


class mood(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_MiraMood('key').not_null().positional().tooltip('tt_mira_mood')]

    def gdo_execute(self):
        args = ('mira.ipc_mood', [self.param_val('key')])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('mira_mood_queued')
