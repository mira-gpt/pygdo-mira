import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.mira.method.ipc_away import ipc_away
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.StarWarsIPC import encode_text


class AwayTranslationTest(unittest.IsolatedAsyncioTestCase):
    async def test_off_cancels_pending_translation_and_closes_effect(self):
        Application.mode(Mode.render_cli)
        method = ipc_away()
        method.param_val = MagicMock(return_value=encode_text('off'))
        method.empty = MagicMock()
        pending = MagicMock()
        mira = SimpleNamespace(_away_task=pending)
        connector = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.mira.method.ipc_away.module_mira.instance', return_value=mira), \
                patch('gdo.mira.method.ipc_away.module_video.instance', return_value=SimpleNamespace(connector=connector)):
            method.gdo_execute()
        pending.cancel.assert_called_once()
        connector.close_effects.assert_called_once_with('away')
        self.assertIsNone(mira._away_task)

    async def test_each_supported_language_translated_once_and_cached(self):
        connector = MagicMock()
        translate_module = MagicMock()
        translate_module.cfg_google_api_key.return_value = 'test-key'
        loader = MagicMock()
        loader.get_module.return_value = translate_module
        video = SimpleNamespace(connector=connector)

        async def translate(text, target, api_key):
            return SimpleNamespace(text={'en': 'Hello', 'de': 'Hallo', 'nl': 'Hallo'}[target])

        with patch('gdo.base.ModuleLoader.ModuleLoader.instance', return_value=loader), \
                patch('gdo.mira.method.ipc_away.LANGUAGES', {'en': 'English', 'de': 'German', 'nl': 'Dutch'}), \
                patch('gdo.video.module_video.module_video.instance', return_value=video), \
                patch('gdo.translate.GTranslate.GTranslate.translate', new_callable=AsyncMock, side_effect=translate) as api:
            await ipc_away.translate(connector, 'Hello', 1.42)
        self.assertEqual(3, api.await_count)
        self.assertEqual({'en', 'de', 'nl'}, {call.kwargs['target'] for call in api.await_args_list})
        connector.away.assert_called_once_with(['Hello', 'Hello', 'Hallo', 'Hallo'], 1.42)

    async def test_microphone_warning_languages_are_the_targets(self):
        from gdo.audio.language import LANGUAGES
        from gdo.mira.method.ipc_away import LANGUAGES as away_languages
        self.assertEqual(('en', 'de', 'ko', 'vi', 'ja', 'sq', 'ru', 'ar'), tuple(away_languages))
        self.assertIs(LANGUAGES, away_languages)

    async def test_cancelled_translation_never_restores_away(self):
        connector = MagicMock()
        task = asyncio.create_task(ipc_away.translate(connector, 'Hello', 1.42))
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        connector.away.assert_not_called()
