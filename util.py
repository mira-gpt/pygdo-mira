"""Small local delivery helpers for an agent's tmux terminal."""

from __future__ import annotations

import os
import json
import math
import pwd
import re
import stat
import subprocess
import time
import uuid


DEFAULT_MIRA_TMUX_USER = 'mira'
MIRA_TMUX_HELPER = '/usr/local/bin/mira-tmux'


def chat_show_context(event: str) -> str:
    """Add configured show context, or honest unknowns outside Dog."""
    try:
        from gdo.mira.module_mira import module_mira
        module = module_mira.instance()
        if module:
            return module.with_liveshow_state(event)
    except Exception:
        pass
    header, separator, body = event.partition('\n')
    if (header == '$chat' or header.startswith('$chat ')) and not re.search(r'(?:^|\s)--mic-lang=', header):
        header += ' --mic-lang=unknown'
    return f'{header} --live=unknown --show-host=unknown{separator}{body}'


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


def validate_agent_name(name: str) -> str:
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name):
        raise ValueError('agent_name must contain only letters, digits, underscores or hyphens for the tmux target')
    return name


def tmux_target() -> str:
    """Use the configured agent's named window unless explicitly overridden."""
    if target := os.environ.get('MIRA_TMUX_TARGET'):
        return target
    from gdo.mira.module_mira import module_mira
    name = validate_agent_name(module_mira.instance().cfg_agent_name())
    # Preserve the established live Mira target; new agents use named windows.
    return 'mira-codex:0.0' if name == 'mira' else f'{name}-codex:{name}'


def read_agent_state(path: str) -> bool | None:
    """Read a recent agent-owned Claude state file, or return unknown."""
    try:
        from gdo.mira.module_mira import module_mira
        module = module_mira.instance()
        agent = module.cfg_agent_name()
        session = module.get_config_val('agent_session_id')
        if not agent or not session:
            return None
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | os.O_NONBLOCK
        fd = os.open(path, flags)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != pwd.getpwnam(tmux_user()).pw_uid
                    or info.st_mode & 0o022 or info.st_size > 4096):
                return None
            data = json.loads(stream.read(4097))
        if data.get('agent') != agent or data.get('session_id') != session:
            return None
        updated = data.get('updated')
        if (isinstance(updated, bool) or not isinstance(updated, (int, float))
                or not math.isfinite(updated) or not 0 <= time.time() - updated <= 600):
            return None
        return {'busy': True, 'idle': False}.get(data.get('state'))
    except Exception:
        return None


def current_agent_busy() -> bool | None:
    """Use the ticker's configured Codex log when it has recent activity."""
    try:
        if path := os.environ.get('MIRA_AGENT_STATE_FILE'):
            return read_agent_state(path)
        from gdo.video.CodexActivity import CodexActivity
        from gdo.video.module_video import module_video
        path = module_video.instance().get_config_val('video_commentary_log')
        if not path or time.time() - os.stat(path).st_mtime > 300:
            return None
        state = CodexActivity.poll(path)
        return {'active': True, 'idle': False}.get(state)
    except Exception:
        # A status hint must never prevent delivery of the event itself.
        return None


def with_busy_hint(text: str, busy: bool | None) -> str:
    """Mark busy events; idle and unknown events carry no busy hint."""
    if busy is not None and not isinstance(busy, bool):
        raise ValueError('busy must be True, False, or None')
    if not busy:
        return text
    return re.sub(r'(?m)^(\$(?!chat_done\b)[a-z][a-z0-9_-]*)(?=\s|$)',
                  lambda match: f'{match.group(1)} --you-busy={int(busy)}', text, count=1)


def send_to_mira(text: str, *, submit: bool = True, target: str | None = None, interrupt: bool = True,
                 busy: bool | None = None) -> None:
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

    text = with_busy_hint(text, current_agent_busy() if busy is None else busy)

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
