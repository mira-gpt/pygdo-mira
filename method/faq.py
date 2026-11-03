from gdo.base.GDO import GDO
from gdo.base.Render import Mode
from gdo.mira.GDO_MiraFAQ import GDO_MiraFAQ
from gdo.table.MethodQueryTable import MethodQueryTable


class faq(MethodQueryTable):
    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.faq'

    def gdo_table(self) -> GDO:
        return GDO_MiraFAQ.table()

    def gdo_table_query(self):
        return super().gdo_table_query().where('mf_answer IS NOT NULL')

    def gdo_table_headers(self):
        table = self.gdo_table()
        return [table.column('mf_question'), table.column('mf_answer')]

    def gdo_order_default(self):
        return 'mf_created DESC'

    def render_gdo(self, entry: GDO, mode: Mode):
        if mode == Mode.render_json:
            return super().render_gdo(entry, mode)
        return f'{entry.gdo_val("mf_question")} — {entry.gdo_val("mf_answer")}'
