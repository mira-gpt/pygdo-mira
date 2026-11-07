import unittest
import httpx
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.mira.ReadAlong import detect_voice, fetch_text, play, split_text, start, stop
from gdo.mira.method.readalong import readalong


class ReadAlongTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_audio_language_filter_accepts_speech_languages(self):
        from gdo.language.GDT_Language import GDT_Language
        from gdo.audio.language import VOICES
        table = MagicMock()
        table.get_by_id.return_value = MagicMock()
        with patch('gdo.language.GDT_Language.GDO_Language.table', return_value=table):
            field = GDT_Language('lang').audiolangs()
            for code in VOICES:
                self.assertIsNotNone(field.to_value(code))
            self.assertIsNone(field.to_value('fr'))
            field.gdo_query()
        table.select.return_value.where.assert_called_with("lang_iso IN ('en', 'de', 'ko', 'vi', 'ja', 'sq', 'ru', 'ar')")

    def test_parts_are_bounded_and_preserve_text(self):
        text = 'Hallo zusammen! ' * 70
        parts = split_text(text)
        self.assertTrue(all(len(part) <= 200 for part in parts))
        self.assertEqual(' '.join(parts), ' '.join(text.split()))

    def test_repeated_special_characters_are_removed(self):
        self.assertEqual(split_text('Hallo === Welt --- ja!!! ok.. ___ ä ää 111'),
                         ['Hallo Welt ja ok.. ä ää 111'])
        self.assertEqual(split_text('links===rechts'), ['links rechts'])
        with self.assertRaises(ValueError):
            split_text('=====')

    async def test_owner_command_queues_all_parts(self):
        method = readalong()
        method.param_value = MagicMock(return_value=False)
        method.param_val = MagicMock(side_effect=lambda key: {'url': 'https://example.org/text', 'lang': 'de'}[key])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.mira.method.readalong.IPC.send_to_dog') as send:
            await method.gdo_execute()
        send.assert_called_once_with('mira.ipc_readalong', ['https://example.org/text', 'de', 'de'])

    async def test_vietnamese_target_is_queued(self):
        method = readalong()
        method.param_value = MagicMock(return_value=False)
        method.param_val = MagicMock(side_effect=lambda key: {'url': 'https://example.org/text', 'lang': 'vi'}[key])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.mira.method.readalong.IPC.send_to_dog') as send:
            await method.gdo_execute()
        send.assert_called_once_with('mira.ipc_readalong', ['https://example.org/text', 'vi', 'vi'])

    async def test_ipc_accepts_vietnamese(self):
        from gdo.mira.method.ipc_readalong import ipc_readalong
        method = ipc_readalong()
        method.empty = MagicMock()
        method.param_val = MagicMock(side_effect=lambda key: {'url': 'https://example.org', 'target': 'vi', 'voice': 'vi'}[key])
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.mira.method.ipc_readalong.start') as start, \
                patch.object(method, '_play', new=MagicMock(return_value=None)):
            await method.gdo_execute()
        start.assert_called_once()

    def test_local_voice_detection(self):
        self.assertEqual(detect_voice('Wir bauen gemeinsam und das ist unser Pakt für die Welt.', 'en'), 'de')
        self.assertEqual(detect_voice('This is the text and we are the people of the world.', 'de'), 'en')
        self.assertEqual(detect_voice('Hallo', 'en'), 'en')

    async def test_stop_cancels_all_readalong_tasks(self):
        import asyncio
        event = asyncio.Event()
        async def pending_job():
            await event.wait()
        first = start(pending_job())
        second = start(pending_job())
        await stop()
        self.assertTrue(first.cancelled())
        self.assertTrue(second.cancelled())

    async def test_fetch_plain_text(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, text='Hallo Welt!')))
        with patch('gdo.mira.ReadAlong.httpx.AsyncClient', return_value=client):
            self.assertEqual(await fetch_text('https://example.org/text'), 'Hallo Welt!')

    async def test_translation_and_speech_are_sequential(self):
        calls = []
        translator = AsyncMock(side_effect=lambda text, **kwargs: SimpleNamespace(text='translated ' + text))
        speech = MagicMock()
        speech.input.return_value = speech
        async def speak():
            calls.append('speech')
        speech.play = AsyncMock(side_effect=speak)
        async def translate(text, **kwargs):
            calls.append('translate')
            return await translator(text, **kwargs)
        with patch('gdo.translate.GTranslate.GTranslate.translate', side_effect=translate), \
                patch('gdo.translate.module_translate.module_translate.instance', return_value=MagicMock(cfg_google_api_key=MagicMock(return_value='test'))), \
                patch('gdo.audio.method.ipc_say.ipc_say', return_value=speech):
            await play(['one', 'two'], 'de', 'de')
        self.assertEqual(calls, ['translate', 'speech', 'translate', 'speech'])
