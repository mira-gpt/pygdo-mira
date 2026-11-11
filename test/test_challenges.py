import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.mira.method.challenges import challenges
from gdo.mira.module_mira import module_mira


class ChallengesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_html)

    async def test_sidebar_links_to_web_page(self):
        page = MagicMock()
        module = module_mira()
        with patch('gdo.base.util.href.href', return_value='/mira_challs.challenges.html') as href:
            module.gdo_init_sidebar(page)
        href.assert_called_once_with('mira_challs', 'challenges')
        page._left_bar.add_field.assert_called_once()
        self.assertEqual('web', challenges().gdo_connectors())

    async def test_page_has_empty_state(self):
        method = challenges()
        with patch.object(method, 't', return_value='Coming soon'):
            card = await method.gdo_execute()
        self.assertIsNotNone(card)
