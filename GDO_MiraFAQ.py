from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_AutoInc import GDT_AutoInc
from gdo.core.GDT_Text import GDT_Text
from gdo.date.GDT_Created import GDT_Created


class GDO_MiraFAQ(GDO):
    def gdo_columns(self) -> list[GDT]:
        return [
            GDT_AutoInc('mf_id'),
            GDT_Text('mf_question').not_null().maxlen(2048),
            GDT_Text('mf_answer').maxlen(4096),
            GDT_Created('mf_created'),
        ]
