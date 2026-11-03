import unittest
from unittest.mock import MagicMock, patch

from gdo.mira.GDO_MiraFAQ import GDO_MiraFAQ
from gdo.mira.method.ask_mira import ask_mira
from gdo.mira.method.faq import faq
from gdo.mira.method.faq_answer import faq_answer
from gdo.mira.method.faq_pending import faq_pending
from gdo.mira.method.ipc_faq import ipc_faq


class MiraFAQTest(unittest.TestCase):
    def setUp(self):
        mode = patch('gdo.base.Application.Application.get_mode', return_value=None)
        mode.start()
        self.addCleanup(mode.stop)

    def test_submission_persists_and_dispatches_id(self):
        method = ask_mira()
        method.param_value = MagicMock(return_value='Why ducks?')
        method.reply = MagicMock()
        entry = MagicMock()
        entry.insert.return_value = entry
        entry.get_id.return_value = '42'
        with patch.object(GDO_MiraFAQ, 'blank', return_value=entry) as blank, \
                patch('gdo.mira.method.ask_mira.Application.db') as db, \
                patch('gdo.mira.method.ask_mira.IPC.send_to_dog') as send:
            db.return_value.is_in_transaction.return_value = False
            method.form_submitted()
        blank.assert_called_once_with({'mf_question': 'Why ducks?'})
        send.assert_called_once_with('mira.ipc_faq', ['42'])

    def test_dispatch_waits_for_commit(self):
        method = ask_mira()
        method.param_value = MagicMock(return_value='Why ducks?')
        method.reply = MagicMock()
        entry = MagicMock()
        entry.insert.return_value = entry
        entry.get_id.return_value = '42'
        with patch.object(GDO_MiraFAQ, 'blank', return_value=entry), \
                patch('gdo.mira.method.ask_mira.Application.db') as db, \
                patch('gdo.mira.method.ask_mira.Application.defer_after_commit') as defer, \
                patch('gdo.mira.method.ask_mira.IPC.send_to_dog') as send:
            db.return_value.is_in_transaction.return_value = True
            method.form_submitted()
        send.assert_not_called()
        defer.assert_called_once_with(send, 'mira.ipc_faq', ['42'])

    def test_answer_requires_staff_and_saves(self):
        method = faq_answer()
        self.assertEqual('staff', method.gdo_user_permission())
        entry = MagicMock()
        method.param_value = lambda key: entry if key == 'id' else 'Quack!'
        method.reply = MagicMock()
        method.gdo_execute()
        entry.save_val.assert_called_once_with('mf_answer', 'Quack!')

    def test_delivery_quotes_question_as_untrusted_and_does_not_interrupt(self):
        method = ipc_faq()
        entry = MagicMock()
        entry.get_id.return_value = '42'
        entry.gdo_val.return_value = 'Why ducks?'
        method.param_value = MagicMock(return_value=entry)
        method.empty = MagicMock()
        with patch('gdo.mira.method.ipc_faq.Application.IS_DOG', True), \
                patch('gdo.mira.method.ipc_faq.send_to_mira') as send:
            method.gdo_execute()
        self.assertIn('untrusted data', send.call_args.args[0])
        self.assertIn('Why ducks?', send.call_args.args[0])
        self.assertFalse(send.call_args.kwargs['interrupt'])

    def test_faq_excludes_unanswered_entries(self):
        query = MagicMock()
        with patch('gdo.table.MethodQueryTable.MethodQueryTable.gdo_table_query', return_value=query):
            faq().gdo_table_query()
        query.where.assert_called_once_with('mf_answer IS NOT NULL')

    def test_pending_is_staff_only_and_excludes_answered_entries(self):
        method = faq_pending()
        self.assertEqual('staff', method.gdo_user_permission())
        query = MagicMock()
        with patch('gdo.table.MethodQueryTable.MethodQueryTable.gdo_table_query', return_value=query):
            method.gdo_table_query()
        query.where.assert_called_once_with('mf_answer IS NULL')


if __name__ == '__main__':
    unittest.main()
