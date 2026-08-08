import os
import tempfile
import unittest
from unittest.mock import patch

from gdo.base.Application import Application
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.connector.Bash import Bash
from gdo.mira.module_mira import CHAT_CONTEXT_MAX_BYTES, MIRA_ADDRESS, module_mira
from gdo.mira.method.overview import overview
from gdo.mira.util import send_to_mira
from gdo.date.Time import Time
from gdotest.TestUtil import cli_plug, reinstall_module, cli_gizmore, GDOTestCase, WebPlug, install_module, web_plug


class module_mira_Test(GDOTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.init(os.path.dirname(__file__ + "/../../../../"))
        loader = ModuleLoader.instance()
        install_module('mira')
        loader.load_modules_db(True)
        WebPlug.COOKIES = {}
        Application.init_cli()
        loader.init_modules(True, True)
        loader.init_cli()

    def test_00_reinstall(self):
        reinstall_module('mira')
        self.assertIs(type(module_mira.instance()), module_mira, "Cannot re-install module mira.")

    def test_01_heartbeat_delay(self):
        self.assertAlmostEqual(1337.420320, module_mira.instance().cfg_heartbeat_delay(), places=6)

    def test_03_overview_cli(self):
        giz =  cli_gizmore()
        out = cli_plug(giz, "$mira.overview")
        self.assertIsNotNone(out, '$mira.overview does not work.')

    def test_04_send_to_mira_cancels_prompt_before_pasting(self):
        with patch('gdo.mira.util.subprocess.run') as run, patch('gdo.mira.util.time.sleep'):
            send_to_mira('$changes gdo/mira/util.py', target='test:0.0')
        calls = [call.args[0] for call in run.call_args_list]
        self.assertEqual(['tmux', 'send-keys', '-t', 'test:0.0', '-l', '--', 'quack'], calls[0])
        self.assertEqual(['tmux', 'send-keys', '-t', 'test:0.0', 'C-c'], calls[1])
        self.assertEqual(['tmux', 'load-buffer', '-b', 'mira-delivery', '-'], calls[2])

    def test_05_channel_forwarding_requires_opt_in(self):
        channel = Bash.get_server().get_or_create_channel('mira_opt_in_test')
        mira = module_mira.instance()
        overview().env_channel(channel).save_config_channel('disabled', '1')
        self.assertFalse(mira.is_channel_enabled(channel))
        overview().env_channel(channel).save_config_channel('disabled', '0')
        self.assertTrue(mira.is_channel_enabled(channel))

    def test_06_mira_address_accepts_natural_punctuation(self):
        for text in ('mira', 'Mira:', 'mira....', 'Mira?'):
            self.assertIsNotNone(MIRA_ADDRESS.match(text), text)

    def test_07_context_discards_expired_lines(self):
        mira = module_mira.instance()
        old = Time.get_date(Application.TIME - mira.cfg_context_max_age() - 1)
        recent = Time.get_date(Application.TIME - 1)
        payload = f'{old} #- old{{bash}} mira: stale\n{recent} #- gizmore{{bash}} mira: current\n'
        self.assertEqual(f'{recent} #- gizmore{{bash}} mira: current\n', mira.recent_context(payload))

    def test_08_context_file_uses_full_small_file_and_complete_large_tail(self):
        mira = module_mira.instance()
        recent = Time.get_date(Application.TIME - 1)
        line = f'{recent} #- gizmore{{bash}} mira: current\n'
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'chat.ibdes')
            with open(path, 'w', encoding='utf-8') as file:
                file.write(line)
            self.assertEqual(line, mira.read_context(path))

            filler = 'x' * CHAT_CONTEXT_MAX_BYTES
            with open(path, 'w', encoding='utf-8') as file:
                file.write(f'{recent} #- gizmore{{bash}} old {filler}\n{line}')
            self.assertEqual(line, mira.read_context(path))

    def test_02_overview_web(self):
        giz =  cli_gizmore()
        out = web_plug("mira.overview.html")
        self.assertIsNotNone(out, 'mira.overview.html does not work.')


if __name__ == '__main__':
    unittest.main()
