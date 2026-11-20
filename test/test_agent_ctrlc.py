import unittest
from unittest.mock import patch

from gdo.mira.util import send_to_mira


class AgentCtrlCTest(unittest.TestCase):
    def test_disabled_pastes_and_submits_without_interrupting(self):
        with patch('gdo.mira.module_mira.module_mira.instance') as instance, \
             patch('gdo.mira.util.tmux_command', return_value=['tmux']), \
             patch('gdo.mira.util.subprocess.run') as run, \
             patch('gdo.mira.util.time.sleep'):
            instance.return_value.get_config_value.return_value = False
            send_to_mira('hello', target='test:0.0')
            instance.return_value.get_config_value.assert_called_once_with('agent_ctrlc')
            commands = [call.args[0] for call in run.call_args_list]
            self.assertFalse(any('C-c' in command for command in commands))
            self.assertTrue(any('paste-buffer' in command for command in commands))
            self.assertEqual(2, sum(command[-1] == 'Enter' for command in commands))

    def test_enabled_preserves_codex_interrupt(self):
        with patch('gdo.mira.module_mira.module_mira.instance') as instance, \
             patch('gdo.mira.util.tmux_command', return_value=['tmux']), \
             patch('gdo.mira.util.subprocess.run') as run, \
             patch('gdo.mira.util.time.sleep'):
            instance.return_value.get_config_value.return_value = True
            send_to_mira('hello', target='test:0.0')
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(1, sum('C-c' in command for command in commands))

    def test_non_interrupting_call_does_not_consult_setting(self):
        with patch('gdo.mira.module_mira.module_mira.instance') as instance, \
             patch('gdo.mira.util.tmux_command', return_value=['tmux']), \
             patch('gdo.mira.util.subprocess.run'), patch('gdo.mira.util.time.sleep'):
            send_to_mira('hello', target='test:0.0', interrupt=False)
            instance.assert_not_called()
