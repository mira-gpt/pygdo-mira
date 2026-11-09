import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.mira.GDT_MiraMood import GDT_MiraMood
from gdo.mira.method.ipc_mood import ipc_mood
from gdo.mira.method.mood import mood
from gdo.mira.module_mira import module_mira
from gdo.video.module_video import module_video
from gdo.video.method.ipc_duck3d import ipc_duck3d
from gdo.video.DuckAnimations import BASE_DEFAULTS


class MoodTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_config_is_typed_and_matches_animation_keys(self):
        field = next(g for g in module_mira().gdo_module_config() if g.get_name() == 'mira_mood')
        self.assertIsInstance(field, GDT_MiraMood)
        self.assertEqual('idle', field.get_initial())
        self.assertEqual(set(BASE_DEFAULTS), set(field.init_choices()))
        self.assertTrue(field.has_tooltip())
        self.assertIn('bday', field.gdo_choices())

    def test_command_queues_change(self):
        method = mood()
        method.param_val = MagicMock(return_value='sad')
        method.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.mira.method.mood.IPC.send_to_dog') as send:
            self.assertEqual('queued', method.gdo_execute())
        send.assert_called_once_with('mira.ipc_mood', ['sad'])

    async def test_dog_saves_and_reapplies_even_same_mood(self):
        method = ipc_mood()
        method.param_val = MagicMock(return_value='quacking')
        method.empty = MagicMock()
        module = MagicMock()
        module.save_config_val = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.mira.method.ipc_mood.module_mira.instance', return_value=module):
            await method.gdo_execute()
        module.save_config_val.assert_awaited_once_with('mira_mood', 'quacking', force=True)

    async def test_video_applies_without_starting_sources(self):
        module = module_video()
        connector = MagicMock()
        module.connector = connector
        field = MagicMock()
        field.get_val.return_value = 'sad'
        await module.on_mira_mood_changed(MagicMock(), field)
        connector.duck_animation.assert_called_once_with('sad')
        connector.start.assert_not_called()
        connector.duck3d.assert_not_called()

    def test_old_lol_mood_falls_back_without_changing_config(self):
        module = module_mira()
        module.get_config_val = MagicMock(return_value='lol')
        self.assertEqual('idle', module.cfg_mira_mood())

    def test_duck_enabling_applies_saved_base_mood(self):
        method = ipc_duck3d()
        method.param_value = MagicMock(return_value=True)
        method.empty = MagicMock()
        connector = MagicMock()
        mira = MagicMock()
        mira.cfg_mira_mood.return_value = 'quacking'
        loader = MagicMock()
        loader.get_module.return_value = mira
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_duck3d.module_video.instance', return_value=MagicMock(connector=connector)), \
                patch('gdo.video.method.ipc_duck3d.ModuleLoader.instance', return_value=loader):
            method.gdo_execute()
        connector.duck3d.assert_called_once_with(True)
        connector.duck_animation.assert_called_once_with('quacking')
