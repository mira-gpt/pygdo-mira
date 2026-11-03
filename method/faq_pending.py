from gdo.mira.GDO_MiraFAQ import GDO_MiraFAQ
from gdo.base.Render import Mode
from gdo.table.MethodQueryTable import MethodQueryTable


class faq_pending(MethodQueryTable):
    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.faq_pending'

    def gdo_user_permission(self) -> str:
        return 'staff'

    def gdo_table(self):
        return GDO_MiraFAQ.table()

    def gdo_table_query(self):
        return super().gdo_table_query().where('mf_answer IS NULL')

    def gdo_table_headers(self):
        table = self.gdo_table()
        return [table.column('mf_id'), table.column('mf_question'), table.column('mf_created')]

    def gdo_order_default(self):
        return 'mf_created ASC'

    def render_gdo(self, entry, mode: Mode):
        if mode == Mode.render_json:
            return super().render_gdo(entry, mode)
        return f'#{entry.get_id()} {entry.gdo_val("mf_question")}'
