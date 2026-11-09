"""Show or dismiss an asynchronously translated away screen."""
from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.video.StarWarsIPC import encode_text


class away(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_RestOfText('message').minlen(1).maxlen(300).not_null()]

    def gdo_execute(self):
        message = self.param_val('message').strip()
        if not message or any(c in message for c in '\r\n\x00'):
            return self.err('video_error', ('Away message must be a non-empty single line.',))
        args = ('mira.ipc_away', [encode_text(message)])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.empty() if Application.IS_DOG else self.reply('mira_away_queued')
