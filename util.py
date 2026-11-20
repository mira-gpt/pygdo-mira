"""Small local delivery helpers for an agent's tmux terminal."""

from __future__ import annotations

import os
import pwd
import re
import subprocess
import time
import uuid


DEFAULT_MIRA_TMUX_USER = 'mira'
MIRA_TMUX_HELPER = '/usr/local/bin/mira-tmux'


def tmux_user() -> str:
    """Return the OS account which owns the agent's tmux socket.

    Agent identity (``agent_name``) is deliberately separate from the local
    account: Simion may run as ``shippi`` while still reacting to ``simion``.
    """
    return os.environ.get('MIRA_TMUX_USER', DEFAULT_MIRA_TMUX_USER)


def tmux_command() -> list[str]:
    """Return the tmux client command for the account that owns the agent pane."""
    user = tmux_user()
    if os.geteuid() == pwd.getpwnam(user).pw_uid:
        return ['tmux']
    helper = os.environ.get('MIRA_TMUX_HELPER')
    if helper:
        return ['sudo', '-n', '-u', user, helper]
    # Mira's established bridge knows her private tmux socket. Other agents
    # use their owner's regular tmux socket unless a dedicated bridge is set.
    if user == DEFAULT_MIRA_TMUX_USER:
        return ['sudo', '-n', '-u', user, MIRA_TMUX_HELPER]
    return ['sudo', '-n', '-u', user, 'tmux']


def tmux_target() -> str:
    """Use the configured agent's session unless explicitly overridden."""
    if target := os.environ.get('MIRA_TMUX_TARGET'):
        return target
    from gdo.mira.module_mira import module_mira
    name = module_mira.instance().cfg_agent_name()
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name):
        raise ValueError('agent_name must contain only letters, digits, underscores or hyphens for the tmux target')
    return f'{name}-codex:0.0'


def send_to_mira(text: str, *, submit: bool = True, target: str | None = None, interrupt: bool = True) -> None:
    """Send literal text to the configured agent's visible tmux terminal.

    ``submit`` uses the Codex editor's reliable submission sequence: two
    trailing spaces followed by two physical Return key events. Set it to
    ``False`` when a caller only wants to prefill the editor. Set ``interrupt``
    to ``False`` to submit a follow-up without sending another Ctrl+C. The
    agent_ctrlc module setting can disable Ctrl+C for all deliveries.
    """
    if not isinstance(text, str) or not text:
        raise ValueError('Mira tmux text must be a non-empty string')
    if '\0' in text:
        raise ValueError('Mira tmux text must not contain NUL bytes')

    destination = target or tmux_target()
    if submit and interrupt:
        from gdo.mira.module_mira import module_mira
        interrupt = bool(module_mira.instance().get_config_value('agent_ctrlc'))
    if submit and interrupt:
        # Avoid an empty Ctrl-C, which exits Mira's terminal. The harmless text
        # makes Ctrl-C cancel the current prompt instead.
        subprocess.run(tmux_command() + ['send-keys', '-t', destination, '-l', '--', 'quack'], check=True)
        time.sleep(0.1)
        subprocess.run(tmux_command() + ['send-keys', '-t', destination, 'C-c'], check=True)
        time.sleep(0.1)

    payload = text + ('  ' if submit else '')
    buffer_name = f'mira-delivery-{uuid.uuid4().hex}'
    subprocess.run(tmux_command() + ['load-buffer', '-b', buffer_name, '-'], input=payload, text=True, check=True)
    try:
        subprocess.run(tmux_command() + ['paste-buffer', '-t', destination, '-b', buffer_name, '-p'], check=True)
    finally:
        subprocess.run(tmux_command() + ['delete-buffer', '-b', buffer_name], check=False)

    if submit:
        subprocess.run(tmux_command() + ['send-keys', '-t', destination, 'Enter'], check=True)
        time.sleep(0.1)
        subprocess.run(tmux_command() + ['send-keys', '-t', destination, 'Enter'], check=True)
