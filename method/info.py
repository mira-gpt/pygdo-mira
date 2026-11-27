from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.mira.GDO_MiraTeam import GDO_MiraTeam
from gdo.mira.module_mira import module_mira


class info(Method):
    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.info'

    def gdo_execute(self):
        module = module_mira.instance()
        domain = Application.config('core.domain', 'pygdo.localhost')
        table = GDO_MiraTeam.table()
        entry = next((team for scheme in ('https', 'http')
                      if (team := table.get_by_vals({'team_url': f'{scheme}://{domain}'}))), None)
        if entry:
            team_info = self.t('msg_mira_team', tuple(entry.column(name).render_cli() for name in
                               ('team_name', 'team_url', 'team_pilot', 'team_agent')))
        else:
            team_info = self.t('mira_info_team_unknown')
        return self.reply('msg_mira_info', (module.cfg_agent_name(), team_info,
                          module.get_config_val('agent_skill_tags') or self.t('mira_info_skills_unset')))
