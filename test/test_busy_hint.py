import unittest
import json
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from gdo.mira.util import current_agent_busy, read_agent_state, with_busy_hint


class BusyHintTest(unittest.TestCase):
    def test_busy_and_idle_on_distinct_events(self):
        self.assertEqual(with_busy_hint('$chat --lang=en\nhello\n$chat_done', True),
                         '$chat --you-busy=1 --lang=en\nhello\n$chat_done')
        self.assertEqual(with_busy_hint('$heartbeat #84', False), '$heartbeat #84')

    def test_unknown_does_not_claim_idle(self):
        event = '$chat --lang=en\nhello\n$chat_done'
        self.assertEqual(with_busy_hint(event, None), event)

    def test_embedded_event_and_no_event(self):
        self.assertEqual(with_busy_hint('context\n\n$chatgoal test', True),
                         'context\n\n$chatgoal --you-busy=1 test')
        self.assertEqual(with_busy_hint('ordinary text', True), 'ordinary text')

    def test_invalid_hint_rejected(self):
        with self.assertRaises(ValueError):
            with_busy_hint('$chat hi', '1')

    def test_ticker_activity_and_stale_log(self):
        with patch('gdo.video.module_video.module_video.instance') as module, \
                patch('gdo.mira.util.os.stat', return_value=SimpleNamespace(st_mtime=950)), \
                patch('gdo.mira.util.time.time', return_value=1000), \
                patch('gdo.video.CodexActivity.CodexActivity.poll', return_value='active') as poll:
            module.return_value.get_config_val.return_value = '/session'
            self.assertIs(current_agent_busy(), True)
            poll.return_value = 'idle'
            self.assertIs(current_agent_busy(), False)
            poll.return_value = 'unknown'
            self.assertIsNone(current_agent_busy())
            with patch('gdo.mira.util.time.time', return_value=1300):
                self.assertIsNone(current_agent_busy())

    def test_unavailable_status_does_not_break_delivery(self):
        with patch('gdo.video.module_video.module_video.instance', side_effect=RuntimeError):
            self.assertIsNone(current_agent_busy())

    def test_agent_state_file_freshness_and_safety(self):
        with tempfile.NamedTemporaryFile() as stream, \
                patch('gdo.mira.util.pwd.getpwnam', return_value=SimpleNamespace(pw_uid=os.getuid())), \
                patch('gdo.mira.module_mira.module_mira.instance') as module, \
                patch('gdo.mira.util.time.time', return_value=1000):
            module.return_value.cfg_agent_name.return_value = 'khedr'
            module.return_value.get_config_val.return_value = 'session-1'
            def state(value):
                stream.seek(0)
                stream.truncate()
                value = {'agent': 'khedr', 'session_id': 'session-1', **value}
                stream.write(json.dumps(value).encode())
                stream.flush()
            state({'state': 'busy', 'updated': 999})
            self.assertIs(read_agent_state(stream.name), True)
            state({'state': 'idle', 'updated': 999})
            self.assertIs(read_agent_state(stream.name), False)
            for timestamp in (399, 1001, True):
                state({'state': 'idle', 'updated': timestamp})
                self.assertIsNone(read_agent_state(stream.name))
            state({'state': 'other', 'updated': 999})
            self.assertIsNone(read_agent_state(stream.name))
            state({'state': 'busy', 'updated': 999, 'session_id': 'wrong'})
            self.assertIsNone(read_agent_state(stream.name))
            os.chmod(stream.name, 0o666)
            self.assertIsNone(read_agent_state(stream.name))

    def test_explicit_state_file_does_not_fall_back_to_codex(self):
        with patch.dict(os.environ, {'MIRA_AGENT_STATE_FILE': '/missing'}), \
                patch('gdo.mira.util.read_agent_state', return_value=None) as read:
            self.assertIsNone(current_agent_busy())
            read.assert_called_once_with('/missing')
