from gdo.base.Application import Application
from gdo.base.GDT import GDT
from gdo.base.IPC import IPC
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.form.GDT_Form import GDT_Form
from gdo.form.MethodForm import MethodForm
from gdo.mira.GDO_MiraFAQ import GDO_MiraFAQ
from gdo.ui.GDT_Panel import GDT_Panel


class ask_mira(MethodForm):
    @classmethod
    def gdo_trigger(cls) -> str:
        return 'mira.ask_mira'

    def gdo_create_form(self, form: GDT_Form) -> None:
        if Application.IS_HTTP:
            form.add_field(GDT_Panel().text('info_mira_ask'))
        form.add_field(GDT_RestOfText('question').not_null().max(2048))
        super().gdo_create_form(form)

    def form_submitted(self) -> GDT:
        entry = GDO_MiraFAQ.blank({'mf_question': self.param_value('question')}).insert()
        args = ('mira.ipc_faq', [entry.get_id()])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('msg_mira_question_queued', (entry.get_id(),))
