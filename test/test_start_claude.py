import os
import unittest
from unittest.mock import patch

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

    def test_launcher_preserves_project_directory_and_exit_code(self):
        with patch.object(start_claude, 'configured_session_id', return_value=None), \
             patch.object(start_claude.subprocess, 'call', return_value=3) as call:
            self.assertEqual(3, start_claude.main())
            call.assert_called_once_with(['claude', '--resume'], cwd=os.getcwd())
