from gdo.base.GDO import GDO
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Name import GDT_Name
from gdo.core.GDT_User import GDT_User
from gdo.net.GDT_Url import GDT_Url


class GDO_MiraTeam(GDO):
    def gdo_columns(self):
        return [GDT_AutoInc('team_id'), GDT_Name('team_name').not_null().unique(),
                GDT_Url('team_url').not_null(), GDT_User('team_pilot'), GDT_User('team_agent')]
