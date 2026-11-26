import unittest
from unittest.mock import AsyncMock, patch

from gdo.mira.module_mira import module_mira


class InstallSidebarTest(unittest.IsolatedAsyncioTestCase):
    async def test_install_does_not_override_video_configuration(self):
        with patch('gdo.mira.Teams.seed_teams') as seed, \
                patch('gdo.video.module_video.module_video.save_config_val', new_callable=AsyncMock) as save:
            await module_mira().gdo_install()
        seed.assert_called_once_with()
        save.assert_not_awaited()
