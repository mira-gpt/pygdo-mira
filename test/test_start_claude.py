import unittest
from unittest.mock import MagicMock, patch

from gdo.mira.scripts import start_claude


class StartClaudeTest(unittest.TestCase):
    def test_empty_session_opens_picker(self):
        for session in (None, ''):
            self.assertEqual(['claude', '--resume'], start_claude.resume_command(session))

    def test_configured_session_resumes_exact_id(self):
        self.assertEqual(['claude', '--resume', 'abc-123'], start_claude.resume_command('abc-123'))

    def test_unsafe_session_is_rejected(self):
        for session in ('--help', 'a b', 'a;rm', 'a/b'):
            with self.subTest(session=session), self.assertRaises(ValueError):
                start_claude.resume_command(session)

    def test_launcher_creates_named_window_and_opens_picker(self):
        with patch.object(start_claude, 'configured_agent', return_value=('khedr', None)), \
             patch.object(start_claude.os, 'getcwd', return_value='/project'), \
             patch.object(start_claude.subprocess, 'run', side_effect=[MagicMock(returncode=1), MagicMock()]) as run, \
             patch.object(start_claude.subprocess, 'call', return_value=3) as call:
            self.assertEqual(3, start_claude.main())
            self.assertEqual(['tmux', 'new-session', '-d', '-s', 'khedr-codex', '-n', 'khedr',
                              '-c', '/project', 'claude', '--resume'], run.call_args_list[1].args[0])
            call.assert_called_once_with(['tmux', 'attach-session', '-t', '=khedr-codex'])

    def test_existing_session_is_attached_without_starting_a_duplicate(self):
        with patch.object(start_claude, 'configured_agent', return_value=('khedr', 'abc-123')), \
             patch.object(start_claude.subprocess, 'run', return_value=MagicMock(returncode=0)) as run, \
             patch.object(start_claude.subprocess, 'call', return_value=0) as call:
            self.assertEqual(0, start_claude.main())
            self.assertEqual(1, run.call_count)
            call.assert_called_once_with(['tmux', 'attach-session', '-t', '=khedr-codex'])
