from unittest.mock import patch
from uuid import uuid4
from pathlib import Path

from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.ModuleLoader import ModuleLoader
from gdo.mira.GDO_MiraFAQ import GDO_MiraFAQ
from gdotest.TestUtil import GDOTestCase, cli_gizmore, cli_plug, cli_user, web_plug


class MiraFAQIntegrationTest(GDOTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.init_test(str(Path(__file__).resolve().parents[3]))
        Application.init_cli()
        loader = ModuleLoader.instance()
        loader.load_modules_db(True)
        loader.init_modules(True, True)
        loader.init_cli()

    async def test_submission_answer_and_public_listing(self):
        question = 'Integration question ' + uuid4().hex
        user = cli_gizmore()
        with patch.object(IPC, 'send_to_dog') as dispatch:
            output = cli_plug(user, '$mira.ask_mira ' + question)
        entry = GDO_MiraFAQ.table().get_by_vals({'mf_question': question})
        self.assertIsNotNone(entry, output)
        self.addCleanup(lambda: GDO_MiraFAQ.table().delete_by_id(entry.get_id()))
        self.assertIsNone(entry.gdo_val('mf_answer'))
        self.assertNotIn(question, cli_plug(user, '$mira.faq'))
        ordinary = cli_user('faq_reader')
        cli_plug(ordinary, '$mira.faq_answer ' + entry.get_id() + ' Unauthorised')
        fresh = GDO_MiraFAQ.table().get_by_id(entry.get_id())
        self.assertIsNone(fresh.gdo_val('mf_answer'))
        dispatch.assert_called_once_with('mira.ipc_faq', [entry.get_id()])
        with patch('gdo.mira.method.ipc_faq.send_to_mira') as deliver, \
                patch.object(Application, 'IS_DOG', True):
            await IPC.execute_dog_event('mira.ipc_faq', [entry.get_id()])
        self.assertIn(question, deliver.call_args.args[0])
        answer = 'Because ducks are curious.'
        output = cli_plug(user, '$mira.faq_answer ' + entry.get_id() + ' ' + answer)
        self.assertIn('answered', output.lower())
        rendered = cli_plug(user, '$mira.faq')
        self.assertIn(question, rendered)
        self.assertIn(answer, rendered)
        web = web_plug('mira.faq.html?_lang=en').exec()
        self.assertIn(question, web)
        self.assertIn(answer, web)

    async def test_web_form_submits_public_question(self):
        question = 'Web question ' + uuid4().hex
        form = web_plug('mira.ask_mira.html?_lang=en').user('gizmore').exec()
        self.assertIn('public FAQ', form)
        with patch.object(IPC, 'send_to_dog') as dispatch:
            output = web_plug('mira.ask_mira.html?_lang=en').user('gizmore').post({
                'question': question, 'submit': '1',
            }).exec()
        entry = GDO_MiraFAQ.table().get_by_vals({'mf_question': question})
        self.assertIsNotNone(entry, output)
        self.addCleanup(lambda: GDO_MiraFAQ.table().delete_by_id(entry.get_id()))
        dispatch.assert_called_once_with('mira.ipc_faq', [entry.get_id()])
