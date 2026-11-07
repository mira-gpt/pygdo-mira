from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.mira.ReadAlong import detect_voice, fetch_text, play, split_text, start
from gdo.audio.language import VOICES


class ipc_readalong(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('url').maxlen(900).not_null().positional(),
                GDT_String('target').ascii().maxlen(4).not_null().positional(),
                GDT_String('voice').ascii().maxlen(2).not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                target = self.param_val('target')
                voice = self.param_val('voice')
                if (target != 'none' and target not in VOICES) or voice not in VOICES:
                    raise ValueError('Unsupported readalong language')
                start(self._play(self.param_val('url'), '' if target == 'none' else target, voice))
            except (ValueError, RuntimeError, OSError) as error:
                Logger.warning(f'Readalong rejected: {error}')
        return self.empty()

    @staticmethod
    async def _play(url, target, voice):
        try:
            text = await fetch_text(url)
            await play(split_text(text), target, voice if target else detect_voice(text, voice))
        except Exception as error:
            Logger.warning(f'Readalong stopped: {error}')
