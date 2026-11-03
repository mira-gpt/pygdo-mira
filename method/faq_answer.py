from gdo.base.GDT import GDT
from gdo.base.Method import Method
from gdo.core.GDT_Object import GDT_Object
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.mira.GDO_MiraFAQ import GDO_MiraFAQ


class faq_answer(Method):
    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.faq_answer'

    def gdo_user_permission(self) -> str:
        return 'staff'

    def gdo_parameters(self) -> list[GDT]:
        return [
            GDT_Object('id').table(GDO_MiraFAQ.table()).not_null(),
            GDT_RestOfText('answer').not_null().max(4096),
        ]

    def gdo_execute(self) -> GDT:
        entry = self.param_value('id')
        entry.save_val('mf_answer', self.param_value('answer'))
        return self.reply('msg_mira_faq_answered', (entry.get_id(),))
