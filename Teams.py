from gdo.core.GDO_Server import GDO_Server
from gdo.core.GDO_User import GDO_User
from gdo.mira.GDO_MiraTeam import GDO_MiraTeam

TEAMS = (
    ('Mogwai', 'https://mogwai.mira-gpt.org', '1129354427', None),
    ('Chico', 'https://chico.mira-gpt.org', '5185951115', '8989806668'),
    ('CGX', 'https://codegeex.dev', '6019524030', '8923487802'),
)


def seed_teams():
    telegram = GDO_Server.get_by_name_or_connector('Telegram')
    bash = GDO_Server.get_by_name_or_connector('Bash')

    def user_id(server, name):
        if not server or not name:
            return None
        user = GDO_User.table().get_by_vals({'user_server': server.get_id(), 'user_name': name})
        return user.get_id() if user else None

    for name, url, pilot, agent in TEAMS:
        pilot_id = user_id(telegram, pilot)
        agent_id = user_id(telegram, agent) if agent else user_id(bash, 'mira')
        if existing := GDO_MiraTeam.table().get_by_vals({'team_name': name}):
            for field, value in (('team_pilot', pilot_id), ('team_agent', agent_id)):
                if value and not existing.gdo_val(field):
                    existing.save_val(field, value)
            continue
        GDO_MiraTeam.blank({
            'team_name': name, 'team_url': url,
            'team_pilot': pilot_id, 'team_agent': agent_id,
        }).insert()
