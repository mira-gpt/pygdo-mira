"""Start or attach to an agent-named tmux session running Claude Code.

Run via start_claude.sh from the agent's original project directory.
"""

import os
from pathlib import Path
import re
import subprocess

from gdo.base.Application import Application
from gdo.mira.util import validate_agent_name


def resume_command(session_id):
    command = ['claude', '--resume']
    if session_id:
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]{0,127}', session_id):
            raise ValueError('Invalid configured agent_session_id')
        command.append(session_id)
    return command


def configured_agent():
    root = Path(__file__).resolve().parents[3]
    Application.init(str(root))
    result = Application.db().select(
        "SELECT (SELECT mv_val FROM gdo_moduleval WHERE mv_module=m.module_id AND mv_key='agent_name'), "
        "(SELECT mv_val FROM gdo_moduleval WHERE mv_module=m.module_id AND mv_key='agent_session_id') "
        "FROM gdo_module m "
        "WHERE m.module_name='mira' AND m.module_enabled=1", False)
    row = result.fetch_row()
    if row is None:
        raise RuntimeError('The mira module is not installed and enabled')
    return validate_agent_name(row[0] or 'mira'), row[1]


def main():
    # Application.init resolves its own root; preserve the caller's working
    # directory because Claude's resume picker is scoped to the project.
    working_directory = os.getcwd()
    agent_name, session_id = configured_agent()
    session = f'{agent_name}-codex'
    exists = subprocess.run(['tmux', 'has-session', '-t', f'={session}'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if exists.returncode:
        command = resume_command(session_id)
        subprocess.run(['tmux', 'new-session', '-d', '-s', session, '-n', agent_name,
                        '-c', working_directory, *command], check=True)
    return subprocess.call(['tmux', 'attach-session', '-t', f'={session}'])


if __name__ == '__main__':
    raise SystemExit(main())
