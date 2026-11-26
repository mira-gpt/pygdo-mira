from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.mira.GDO_MiraTeam import GDO_MiraTeam


class team(Method):
    def gdo_parameters(self):
        return [GDT_Enum('name').choices({'mogwai': 'Mogwai', 'chico': 'Chico', 'cgx': 'CGX'}).not_null().positional()]

    def gdo_execute(self):
        entry = GDO_MiraTeam.table().get_by_vals({'team_name': self.param_value('name')})
        if not entry:
            return self.reply('err_mira_team_missing')
        return self.reply('msg_mira_team', tuple(entry.column(name).render_cli() for name in
                          ('team_name', 'team_url', 'team_pilot', 'team_agent')))
