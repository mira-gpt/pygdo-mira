"""Start Claude's interactive resume flow in the current terminal.

Run via start_claude.sh from the agent's original project directory, inside
its tmux session.
"""

import os
from pathlib import Path
import re
import subprocess

from gdo.base.Application import Application


def resume_command(session_id):
    command = ['claude', '--resume']
    if session_id:
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]{0,127}', session_id):
            raise ValueError('Invalid configured agent_session_id')
        command.append(session_id)
    return command


def configured_session_id():
    root = Path(__file__).resolve().parents[3]
    Application.init(str(root))
    result = Application.db().select(
        "SELECT mv.mv_val FROM gdo_module m LEFT JOIN gdo_moduleval mv "
        "ON mv.mv_module=m.module_id AND mv.mv_key='agent_session_id' "
        "WHERE m.module_name='mira' AND m.module_enabled=1", False)
    row = result.fetch_row()
    if row is None:
        raise RuntimeError('The mira module is not installed and enabled')
    return row[0]


def main():
    # Application.init resolves its own root; preserve the caller's working
    # directory because Claude's resume picker is scoped to the project.
    working_directory = os.getcwd()
    command = resume_command(configured_session_id())
    return subprocess.call(command, cwd=working_directory)


if __name__ == '__main__':
    raise SystemExit(main())
