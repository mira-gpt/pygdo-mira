from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.video.MicTicker import MicTicker
from gdo.video.StarWarsIPC import decode_text


class ipc_btx(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').ascii().maxlen(1024).not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                MicTicker.enqueue(decode_text(self.param_val('payload')))
            except (ValueError, RuntimeError) as error:
                Logger.warning(f'Microphone ticker enqueue failed: {error}')
        return self.empty()
