import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Cache import Cache
from gdo.base.Render import Mode
from gdo.mira.GDO_MiraTeam import GDO_MiraTeam
from gdo.mira.Teams import TEAMS, seed_teams
from gdo.mira.method.team import team
from gdo.mira.method.teams import teams


class TeamsTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)
        Cache.init()

    def test_table_columns_and_name_parameter(self):
        self.assertEqual(['team_id', 'team_name', 'team_url', 'team_pilot', 'team_agent'],
                         [column.get_name() for column in GDO_MiraTeam().gdo_columns()])
        self.assertEqual('Chico', team().gdo_parameters()[0].to_value('chico'))
        self.assertFalse(teams().gdo_paginated())

    def test_seed_resolves_existing_local_user_ids(self):
        server = MagicMock()
        server.get_id.return_value = '5'
        user = MagicMock()
        user.get_id.return_value = '42'
        with patch('gdo.mira.Teams.GDO_Server.get_by_name_or_connector', return_value=server), \
             patch('gdo.mira.Teams.GDO_User.table') as users, \
             patch('gdo.mira.Teams.GDO_MiraTeam.table') as table, \
             patch('gdo.mira.Teams.GDO_MiraTeam.blank') as blank:
            users.return_value.get_by_vals.return_value = user
            table.return_value.get_by_vals.return_value = None
            seed_teams()
        self.assertEqual(len(TEAMS), blank.call_count)
        self.assertEqual('42', blank.call_args_list[1].args[0]['team_pilot'])
        users.return_value.get_by_vals.assert_any_call({'user_server': '5', 'user_name': '5185951115'})

    def test_missing_team_returns_reply(self):
        method = team()
        with patch.object(method, 'param_value', return_value='Chico'), \
             patch('gdo.mira.method.team.GDO_MiraTeam.table') as table, \
             patch.object(method, 'reply') as reply:
            table.return_value.get_by_vals.return_value = None
            method.gdo_execute()
        reply.assert_called_once_with('err_mira_team_missing')
