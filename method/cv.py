from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.message.GDT_HTML import GDT_HTML
from gdo.ui.GDT_Card import GDT_Card


class cv(Method):
    """A playful fictional curriculum vitae for Mira."""

    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.cv'

    async def gdo_execute(self) -> GDT:
        card = GDT_Card().title('mt_mira_cv')
        card.get_content().add_field(GDT_HTML().text(self.t('msg_mira_cv', ())))
        return card
