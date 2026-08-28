import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gdo.base.Application import Application
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.connector.Bash import Bash
from gdo.mira.module_mira import CHAT_CONTEXT_MAX_BYTES, MIRA_ADDRESS, module_mira
from gdo.mira.method.enabled import enabled
from gdo.mira.method.heartbeat import heartbeat
from gdo.mira.method.shadowlamb import shadowlamb
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

    def test_01b_users_may_talk_to_mira_by_default(self):
        setting = next(gdt for gdt in module_mira.instance().gdo_user_config()
                       if gdt.get_name() == 'mira_enabled')
        self.assertEqual('1', setting.get_initial())

    def test_03_enabled_cli(self):
        giz =  cli_gizmore()
        out = cli_plug(giz, "$mira 1")
        self.assertIn('Mira is now enabled', out)

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
        enabled().env_channel(channel).save_config_channel('disabled', '1')
        self.assertFalse(mira.is_channel_enabled(channel))
        enabled().env_channel(channel).save_config_channel('disabled', '0')
        self.assertTrue(mira.is_channel_enabled(channel))

    def test_05a_heartbeat_is_channel_only_and_disabled_by_default(self):
        channel = Bash.get_server().get_or_create_channel('mira_heartbeat_test')
        method = heartbeat().env_channel(channel)
        self.assertEqual('1', heartbeat._config_channel_for('disabled').get_initial())
        # The test channel may survive a prior test run, so establish the
        # expected disabled state before testing the explicit opt-in.
        method.save_config_channel('disabled', '1')
        self.assertTrue(method.get_config_channel_value('disabled'))
        self.assertEqual(194, method.get_config_channel_value('delay'))
        mira = module_mira.instance()
        enabled().env_channel(channel).save_config_channel('disabled', '1')
        self.assertFalse(mira.heartbeat_enabled(channel))
        enabled().env_channel(channel).save_config_channel('disabled', '0')
        method.save_config_channel('disabled', '0')
        self.assertFalse(method.get_config_channel_value('disabled'))
        self.assertTrue(mira.heartbeat_enabled(channel))
        mira.reset_heartbeat(channel, 100)
        self.assertFalse(mira.heartbeat_due(channel, 100, 293))
        self.assertTrue(mira.heartbeat_due(channel, 100, 294))
        self.assertEqual('hb', heartbeat.gdo_trig())

    def test_05b_ibdes_uses_canonical_channel_id(self):
        channel = Bash.get_server().get_or_create_channel('mira_ibdes_id_test')
        self.assertEqual(f'#{channel.get_id()}', module_mira.ibdes_channel(channel))
        self.assertEqual('#-', module_mira.ibdes_channel(None))

    def test_05c_ibdes_keeps_the_incoming_reply_connector(self):
        effective = SimpleNamespace(name='gizmore-web')
        reply_to = SimpleNamespace(name='gizmore-ws')
        message = SimpleNamespace(_env_user=effective, _env_reply_to=reply_to, _env_target_user=None)
        self.assertIs(reply_to, module_mira.ibdes_author(message, False))
        self.assertIs(effective, module_mira.ibdes_author(message, True))

    def test_06_mira_address_accepts_natural_punctuation(self):
        for text in ('mira', 'Mira:', 'mira....', 'Mira?', 'hello, mira!', 'tell mira this'):
            self.assertIsNotNone(MIRA_ADDRESS.search(text), text)
        for text in ('mirage', 'Amira', 'miras'):
            self.assertIsNone(MIRA_ADDRESS.search(text), text)

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

    def test_08b_compacts_repeated_chat_newlines(self):
        compact = module_mira.compact_chat_newlines
        self.assertEqual('one\ntwo', compact('one\n\ntwo'))
        self.assertEqual('one\ntwo', compact('one\r\n\r\ntwo'))
        self.assertEqual('one\ntwo', compact('one\r\r\ntwo'))

    def test_08bb_does_not_forward_the_mira_channel_toggle(self):
        self.assertTrue(module_mira.is_toggle_command('$mira 1', '$'))
        self.assertTrue(module_mira.is_toggle_command('.mira 0', '.'))
        self.assertFalse(module_mira.is_toggle_command('mira 1', '$'))
        self.assertFalse(module_mira.is_toggle_command('$mira hello', '.'))

    def test_08c_outbound_ibdes_uses_connector_payload(self):
        message = SimpleNamespace(_message='$say.in 5 --prefix=0 hello', _result='hello')
        self.assertEqual('hello', module_mira.ibdes_payload(message, True))
        self.assertEqual('$say.in 5 --prefix=0 hello', module_mira.ibdes_payload(message, False))

    def test_09_shadowlamb_filters_only_new_lamb3_replies(self):
        payload = (
            '2026-08-09 00:59:15.203041 #- Dog{wechall} .ping\n'
            '2026-08-09 00:59:15.288864 #- Lamb3{wechall} pong!\n'
            '2026-08-09 00:59:15.346493 #- other{wechall} nope\n'
        )
        self.assertEqual(
            '2026-08-09 00:59:15.288864 #- Lamb3{wechall} pong!\n',
            shadowlamb.reply_lines(payload, 'Lamb3'))

    def test_10_health_reports_transitions_but_not_its_initial_baseline(self):
        mira = module_mira.instance()
        self.assertEqual([], mira.health_changes({'Telegram': True, 'WeChall': True}))
        self.assertEqual([], mira.health_changes({'Telegram': True, 'WeChall': True}))
        self.assertEqual([('Telegram', False)], mira.health_changes({'Telegram': False, 'WeChall': True}))

    def test_11_shadowlamb_reads_only_appended_lamb3_replies(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Lamb3.ibdes'
            with open(path, 'w', encoding='utf-8') as file:
                file.write('2026-08-09 #- Dog{wechall} .ping\n')
            offset = os.path.getsize(path)
            with open(path, 'a', encoding='utf-8') as file:
                file.write('2026-08-09 #- Lamb3{wechall} pong!\n')
            offset, replies = shadowlamb.read_new_replies(path, offset, 'Lamb3')
            self.assertEqual(os.path.getsize(path), offset)
            self.assertEqual('2026-08-09 #- Lamb3{wechall} pong!\n', replies)

if __name__ == '__main__':
    unittest.main()
