import os
import unittest
from unittest.mock import patch

from gdo.mira.util import tmux_target


class TmuxTargetTest(unittest.TestCase):
    def test_default_uses_configured_agent_name(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch('gdo.mira.module_mira.module_mira.instance') as instance:
            for name in ('mira', 'khedr', 'simion'):
                instance.return_value.cfg_agent_name.return_value = name
                self.assertEqual('mira-codex:0.0' if name == 'mira' else f'{name}-codex:{name}', tmux_target())

    def test_explicit_target_takes_priority(self):
        with patch.dict(os.environ, {'MIRA_TMUX_TARGET': 'custom:window.1'}, clear=True), \
             patch('gdo.mira.module_mira.module_mira.instance') as instance:
            self.assertEqual('custom:window.1', tmux_target())
            instance.assert_not_called()

    def test_unsafe_agent_names_do_not_target_another_pane(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch('gdo.mira.module_mira.module_mira.instance') as instance:
            for name in ('', 'bad:name', 'bad.name', 'a b'):
                instance.return_value.cfg_agent_name.return_value = name
                with self.subTest(name=name), self.assertRaises(ValueError):
                    tmux_target()
