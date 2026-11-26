from gdo.base.Render import Mode
from gdo.mira.GDO_MiraTeam import GDO_MiraTeam
from gdo.table.MethodQueryTable import MethodQueryTable


class teams(MethodQueryTable):
    def gdo_table(self):
        return GDO_MiraTeam.table()

    def gdo_paginated(self):
        return False

    def gdo_ordered(self):
        return False

    def gdo_filtered(self):
        return False

    def gdo_searched(self):
        return False

    def gdo_table_headers(self):
        return [self.gdo_table().column(name) for name in
                ('team_name', 'team_url', 'team_pilot', 'team_agent')]

    def render_gdo(self, team, mode):
        if mode == Mode.render_json:
            return super().render_gdo(team, mode)
        return ' — '.join(str(team.column(name).render(mode)) for name in
                          ('team_name', 'team_url', 'team_pilot', 'team_agent'))
