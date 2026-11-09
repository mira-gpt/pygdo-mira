"""Run away translation in Dog without blocking the chat event loop."""
import asyncio

from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.audio.language import LANGUAGES
from gdo.mira.module_mira import module_mira
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class ipc_away(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').maxlen(1024).not_null().positional()]

    def gdo_execute(self):
        if not Application.IS_DOG:
            return self.empty()
        mira = module_mira.instance()
        old = getattr(mira, '_away_task', None)
        if old:
            old.cancel()
        try:
            text = decode_text(self.param_val('payload')).strip()
            connector = module_video.instance().connector
            if text.casefold() == 'off':
                connector.close_effects('away')
                mira._away_task = None
            else:
                cycle = mira.get_config_value('live_away_msg_cycle_time') or 1.42
                connector.away([text], cycle)
                mira._away_task = asyncio.create_task(self.translate(connector, text, cycle))
        except (ValueError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Away screen failed: {error}')
        return self.empty()

    @staticmethod
    async def translate(connector, text, cycle):
        try:
            from gdo.base.ModuleLoader import ModuleLoader
            from gdo.translate.GTranslate import GTranslate
            module = ModuleLoader.instance().get_module('translate')
            if not module or not module.cfg_google_api_key():
                Logger.warning('Away translation unavailable; original text remains visible')
                return
            # Match the languages cycled by the microphone warning overlay.
            codes = tuple(LANGUAGES)
            semaphore = asyncio.Semaphore(4)

            async def one(code):
                async with semaphore:
                    try:
                        result = await GTranslate.translate(text, target=code, api_key=module.cfg_google_api_key())
                        return result.text.strip()[:300]
                    except Exception:
                        Logger.warning(f'Away translation unavailable for {code}')
                        return ''

            translations = await asyncio.gather(*(one(code) for code in codes))
            messages = [text] + [value for value in translations if value]
            if module_video.instance().connector is connector:
                connector.away(messages, cycle)
        except Exception as error:
            Logger.warning(f'Away translation failed: {error}')
