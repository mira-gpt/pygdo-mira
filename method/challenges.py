from gdo.base.Method import Method
from gdo.message.GDT_HTML import GDT_HTML
from gdo.ui.GDT_Card import GDT_Card


class challenges(Method):
    def gdo_connectors(self):
        return 'web'

    async def gdo_execute(self):
        card = GDT_Card().title('mt_mira_challenges')
        card.get_content().add_field(GDT_HTML().text(self.t('msg_mira_challenges_empty', ())))
        return card
