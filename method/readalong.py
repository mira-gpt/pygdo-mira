import msgspec.json
from urllib.parse import urlsplit

from gdo.audio.language import VOICES, speech_language
from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.core.GDT_Bool import GDT_Bool


class readalong(Method):
    @classmethod
    def gdo_trig(cls):
        return 'readalong'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('url').maxlen(2048).positional().tooltip('tt_mira_readalong_url'),
                GDT_Bool('stop').initial('0').tooltip('tt_mira_readalong_stop'),
                GDT_Enum('lang').choices({'en': 'English', 'de': 'Deutsch'}).tooltip('tt_mira_readalong_lang')]

    async def gdo_execute(self):
        try:
            if self.param_value('stop'):
                args = ('mira.ipc_stopreadalong', [])
                if Application.db().is_in_transaction():
                    Application.defer_after_commit(IPC.send_to_dog, *args)
                else:
                    IPC.send_to_dog(*args)
                return self.reply('mira_readalong_stop_queued')
            url = self.param_val('url')
            if not url:
                raise ValueError('Provide a URL or --stop')
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Use an HTTP or HTTPS URL without credentials')
            target = self.param_val('lang') or ''
            voice = speech_language(self, target or None)
            if voice not in VOICES:
                raise ValueError('No speech voice for this language; select --lang=en or --lang=de')
            args = ('mira.ipc_readalong', [url, target or 'none', voice])
            if len(msgspec.json.encode(args[1])) > IPC.MAX_EVENT_ARG_SIZE:
                raise ValueError('URL exceeds IPC limit')
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
            return self.reply('mira_readalong_queued')
        except (ValueError, RuntimeError, OSError) as error:
            return self.err('mira_readalong_error', (str(error),))
