import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.mira.method.info import info


class InfoTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_local_team_pilot_and_skills(self):
        method = info()
        entry = MagicMock()
        entry.column.side_effect = lambda name: MagicMock(render_cli=MagicMock(return_value=name))
        module = MagicMock()
        module.cfg_agent_name.return_value = 'mira'
        module.get_config_val.return_value = 'GDO backend'
        with patch('gdo.mira.method.info.Application.config', return_value='example.test'), \
             patch('gdo.mira.method.info.module_mira.instance', return_value=module), \
             patch('gdo.mira.method.info.GDO_MiraTeam.table') as table, \
             patch.object(method, 't', return_value='team with pilot'), \
             patch.object(method, 'reply') as reply:
            table.return_value.get_by_vals.return_value = entry
            method.gdo_execute()
        table.return_value.get_by_vals.assert_called_once_with({'team_url': 'https://example.test'})
        reply.assert_called_once_with('msg_mira_info', ('mira', 'team with pilot', 'GDO backend'))
        entry.column.assert_any_call('team_pilot')

    def test_unknown_team_and_empty_skills(self):
        method = info()
        module = MagicMock()
        module.cfg_agent_name.return_value = 'agent'
        module.get_config_val.return_value = ''
        with patch('gdo.mira.method.info.Application.config', return_value='unknown.test'), \
             patch('gdo.mira.method.info.module_mira.instance', return_value=module), \
             patch('gdo.mira.method.info.GDO_MiraTeam.table') as table, \
             patch.object(method, 't', side_effect=lambda key: key), \
             patch.object(method, 'reply') as reply:
            table.return_value.get_by_vals.return_value = None
            method.gdo_execute()
        reply.assert_called_once_with('msg_mira_info', ('agent', 'mira_info_team_unknown', 'mira_info_skills_unset'))
