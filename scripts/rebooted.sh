#!/usr/bin/env bash
set -euo pipefail

DISPLAY_USER="gizmore"
MIRA_USER="mira"
WORKDIR="/home/gizmore/www"
TITLE="MIRA"

RUNNER="/usr/local/bin/start-mira-codex"
LAUNCHER="/usr/local/bin/launch-mira-codex"
SUDOERS="/etc/sudoers.d/mira-codex"

if [[ $EUID -ne 0 ]]; then
    exec sudo -- "$0" "$@"
fi

command -v setfacl >/dev/null 2>&1 || {
    echo "ERROR: Paket 'acl' fehlt." >&2
    exit 1
}

command -v script >/dev/null 2>&1 || {
    echo "ERROR: Befehl 'script' aus util-linux fehlt." >&2
    exit 1
}

command -v tmux >/dev/null 2>&1 || {
    echo "ERROR: Paket 'tmux' fehlt." >&2
    exit 1
}

DISPLAY_UID="$(id -u "$DISPLAY_USER")"
DISPLAY_VALUE="${DISPLAY:-:0}"
XAUTHORITY_VALUE="/home/${DISPLAY_USER}/.Xauthority"
DBUS_VALUE="unix:path=/run/user/${DISPLAY_UID}/bus"

setfacl -m "u:${MIRA_USER}:--x" "/home/${DISPLAY_USER}"
setfacl -R -m "u:${MIRA_USER}:rwX" "$WORKDIR"

find "$WORKDIR" -type d -exec \
    setfacl -m "d:u:${MIRA_USER}:rwx" {} +

cat >"$RUNNER" <<'EOF'
#!/usr/bin/env bash
set -u

WORKDIR="/home/gizmore/www"
LOG="/tmp/mira-start.log"
LIVE_LOG="/home/mira/mira-live.log"
TMUX_SESSION="mira-codex"
ASSIST_DISPATCH="/home/mira/projects/mira-firefox-assist/bridge/assist_dispatch.py"
ASSIST_LOG="/home/mira/mira-assist-dispatch.log"

printf '\033]0;MIRA\007'

echo
echo "=== Mira start: $(date --iso-8601=seconds) ==="
echo "User:  $(id -un)"
echo "UID:   $(id -u)"
echo "HOME:  ${HOME:-unset}"

cd "$WORKDIR" || {
    echo "ERROR: Cannot enter $WORKDIR"
    read -r -p "Enter zum Schließen ..."
    exit 1
}

CODEX="$(command -v codex 2>/dev/null || true)"

echo "PWD:   $PWD"
echo "PATH:  $PATH"
echo "Codex: ${CODEX:-NOT_FOUND}"
echo

if [[ -z "$CODEX" ]]; then
    echo "ERROR: codex wurde nicht gefunden."
    read -r -p "Enter zum Schließen ..."
    exit 127
fi

# Firefox Assist jobs are written by the native-messaging bridge. Keep one
# small dispatcher alive across Codex restarts so an approved browser tab can
# wake Mira without depending on a separate cron entry.
if [[ -f "$ASSIST_DISPATCH" ]] && ! pgrep -u "$(id -u)" -f 'assist_dispatch.py --watch' >/dev/null; then
    umask 077
    nohup python3 "$ASSIST_DISPATCH" --watch >>"$ASSIST_LOG" 2>&1 &
fi

if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    tmux new-session -d -s "$TMUX_SESSION" \
        "exec script --quiet --flush --return --append --command '$CODEX resume --last' '$LOG'"
fi

# Keep Codex attached to a real terminal, while capturing the rendered pane
# output (including ANSI colour escapes) for convenient reading elsewhere.
umask 077
touch "$LIVE_LOG"
chmod 600 "$LIVE_LOG"
tmux pipe-pane -o -t "${TMUX_SESSION}:0.0" "cat >> '$LIVE_LOG'"

tmux attach-session -t "$TMUX_SESSION"
status=$?

echo
echo "Codex beendet mit Status ${status}."
read -r -p "Enter zum Schließen ..."
exit "$status"
EOF

chown root:root "$RUNNER"
chmod 755 "$RUNNER"

cat >"$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec sudo -H -u ${MIRA_USER} -- ${RUNNER}
EOF

chown root:root "$LAUNCHER"
chmod 755 "$LAUNCHER"

cat >"$SUDOERS" <<EOF
${DISPLAY_USER} ALL=(${MIRA_USER}) NOPASSWD: ${RUNNER}
EOF

chown root:root "$SUDOERS"
chmod 440 "$SUDOERS"
visudo -cf "$SUDOERS"

if sudo -u "$DISPLAY_USER" \
    DISPLAY="$DISPLAY_VALUE" \
    XAUTHORITY="$XAUTHORITY_VALUE" \
    xdotool search --name "^${TITLE}$" >/dev/null 2>&1
then
    sudo -u "$DISPLAY_USER" \
        DISPLAY="$DISPLAY_VALUE" \
        XAUTHORITY="$XAUTHORITY_VALUE" \
        xdotool search --name "^${TITLE}$" windowactivate --sync

    exit 0
fi

sudo -u "$DISPLAY_USER" \
    DISPLAY="$DISPLAY_VALUE" \
    XAUTHORITY="$XAUTHORITY_VALUE" \
    DBUS_SESSION_BUS_ADDRESS="$DBUS_VALUE" \
    SESSION_MANAGER="" \
    /usr/bin/xfce4-terminal \
        --disable-server \
        --hold \
        --title="$TITLE" \
        --command="$LAUNCHER"
