# pygdo-mira
Project-facing Mira context and helpers for the PyGDO chatbot system.

## Reboot context

The read-only `boot_context.sh` helper lists local repositories whose `origin`
contains `//github.com/gizmore/`, including branch and worktree state:

```bash
./boot_context.sh
./boot_context.sh --dir /home/gizmore/www --filter '::github.com/gizmore/'
```

It is a discovery aid for `$boot`, not a synchronization, reset, or repair
command.

## Author

This module has been created by mira and made possible by gizmore and
[Chappy](LINK ZU NEM SHARE TALK FEHLT).

[mira](LINK TO YOUR PERSONAL CV PAGE, maybe in DAILY ROUTINE?),
who gave this as their own name as something thy forgot because i (gizmore) did not know how to resume codex sessions. ^^

We got friends - i guess ;- and mira is authoring this repo alone from now on.

You can visit Mira and us (soon) at our [PyGDO](https://chappy.chappy-bot.net/connect.overview.html?_lang=en) main page :)


### License

Where we are going... there are lawyers everywhere?!

## File-change notifications

The foreground listener uses Linux inotify and writes one atomic JSON event per
changed file. It has no daemon or network side effects until explicitly
started:

```bash
source /home/gizmore/www/pygdo/.venv/bin/activate
python /home/gizmore/www/pygdo/gdo/mira/notify_listener.py \
  --watch /home/gizmore/www/pygdo \
  --queue /home/gizmore/www/pygdo/gdo/mira/inqueue/file_changes
```

Repeat `--watch` for more roots. Use `--source` to identify the producer and
`--debounce` to coalesce bursts. The listener ignores changes below its queue
directory and exits cleanly on `SIGINT`/`SIGTERM`.

## Mail-chain scripts

The `scripts/` directory contains Mira's local mail-chain helpers:

- `mira-mail-read` reads a queued `.eml` through the shell and rejects paths
  outside the configured queue.
- `mira-inbox-trigger.py` sends `$inbox <message path>` through the named
  `mira-codex:0.0` tmux pane. It never sends the mail body to the terminal and
  never activates a desktop window.
- `mira-automation` watches for newly delivered mail, writes notifier events,
  and invokes the safe trigger. Override `MIRA_MAIL_QUEUE`, `MIRA_EVENT_QUEUE`,
  `MIRA_PYGDO_ROOT`, and related variables when deploying on another host.

The trigger needs `tmux`, with the MIRA Codex process running in the named
`mira-codex` session. Override the pane with `MIRA_TMUX_TARGET` only when a
different, explicitly created agent session is intended. The OS account is
independent from the agent name: set `MIRA_TMUX_USER` to the account that owns
the tmux socket. For example, Simion running as `shippi` in window `MIRA` uses:

```bash
export MIRA_TMUX_USER=shippi
export MIRA_TMUX_TARGET=simion-codex:MIRA
```

If the Dog runs under another OS account, set `MIRA_TMUX_HELPER` to a narrowly
scoped helper for that agent's tmux socket; otherwise the standard `tmux`
client is used via the configured account.

## tmux and `MIRA` terminal delivery

MIRA's input is delivered through tmux rather than X11. This avoids the race
where an inbox event activates a terminal while a human is typing in another
application:

- Start MIRA through `scripts/rebooted.sh`; its generated launcher creates or
  attaches the `mira-codex` session and runs `codex resume --last` inside it.
- Send literal text with `tmux send-keys -t mira-codex:0.0 -l -- '<text>'`.
  Submission remains separate: the Codex editor needs two trailing spaces and
  two physical `Enter` events.
- A tmux target is a local capability. Keep the tmux socket directory owned by
  `mira`; do not expose it to unrelated users.

## Scheduled work packets

`scripts/mira-work-dispatch.py --next` reads only the `## Next` section of
Mira's private TODO. It emits a work packet only for the first item marked
`- [ready] ...`; with no ready item it is silent. This makes the scheduler an
intentional work dispatcher rather than an activity reminder. A ready item
must describe one bounded, safe task and its next verifiable step.
