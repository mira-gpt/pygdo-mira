import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parent.parent / 'scripts' / 'mira-dog-launch'


class DogBackupStartTest(unittest.TestCase):
    def run_launcher(self, backup_exit):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / 'gdo' / 'mira' / 'scripts' / 'mira-dog-launch'
            script.parent.mkdir(parents=True)
            script.write_bytes(SOURCE.read_bytes())
            backup = root / 'gdo_backup.sh'
            backup.write_text('#!/bin/sh\nprintf "backup %s\\n" "$1"\nexit %d\n' % ('%s', backup_exit))
            backup.chmod(0o700)
            python = root / 'fake-python'
            python.write_text('#!/bin/sh\necho DOG_STARTED\n')
            python.chmod(0o700)
            log = root / 'dog.log'
            result = subprocess.run(['bash', str(script), '--config=protected/custom.toml'],
                                    env={**os.environ, 'PYGDO_PYTHON': str(python),
                                         'MIRA_DOG_LOG': str(log)}, capture_output=True)
            return result.returncode, log.read_text()

    def test_successful_backup_precedes_start_with_selected_config(self):
        code, log = self.run_launcher(0)
        self.assertEqual(0, code)
        self.assertIn('backup --config=protected/custom.toml', log)
        self.assertLess(log.index('backup '), log.index('DOG_STARTED'))

    def test_failed_backup_aborts_start(self):
        code, log = self.run_launcher(1)
        self.assertNotEqual(0, code)
        self.assertIn('Dog not started: backup failed.', log)
        self.assertNotIn('DOG_STARTED', log)
