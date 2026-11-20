import unittest
from unittest.mock import AsyncMock, patch

from gdo.mira.module_mira import module_mira


class MiraVideoInstallTest(unittest.IsolatedAsyncioTestCase):
    async def test_install_enables_video_stream_sidebar(self):
        video = AsyncMock()
        with patch('gdo.video.module_video.module_video.instance', return_value=video):
            await module_mira().gdo_install()
        video.save_config_val.assert_awaited_once_with('video_stream_sidebar', '1')
