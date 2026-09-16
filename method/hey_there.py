from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.base.Util import module_enabled
from gdo.core.connector.Web import Web
from gdo.message.GDT_HTML import GDT_HTML
from gdo.ui.GDT_Card import GDT_Card
from gdo.user.GDT_ProfileLink import GDT_ProfileLink


class hey_there(Method):
    """Introduce Mira and link to her PyGDO profile."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.hey_there'

    async def gdo_execute(self) -> GDT:
        mira = await Web.get_server().get_or_create_user('mira')
        card = GDT_Card().title('mt_mira_hey_there')
        card.get_content().add_field(GDT_HTML().text(self.t('msg_mira_hey_there', ())))
        card.get_footer().add_field(
            GDT_ProfileLink().user(mira).with_avatar(module_enabled('avatar'))
        )
        return card
