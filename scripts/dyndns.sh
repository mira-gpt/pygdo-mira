#!/usr/bin/env bash
# Update the managed Namecheap Dynamic DNS records.
#
# Run this as root. Keep the Dynamic DNS password in the root-only config
# /etc/mira/dyndns.env, never in this repository.

set -euo pipefail

readonly CONFIG_FILE="${MIRA_DYNDNS_CONFIG:-/etc/mira/dyndns.env}"
readonly UPDATE_URL='https://dynamicdns.park-your-domain.com/update'

if [[ $EUID -ne 0 ]]; then
    echo 'dyndns.sh must be run as root.' >&2
    exit 1
fi

if [[ ! -r "$CONFIG_FILE" ]]; then
    cat >&2 <<EOF
Missing $CONFIG_FILE.
Create it as root with mode 0600, for example:
  NAMECHEAP_DDNS_PASSWORD='replace-with-a-rotated-key'
EOF
    exit 1
fi

config_mode=$(stat -c '%a' "$CONFIG_FILE")
if (( (8#$config_mode & 0077) != 0 )); then
    echo "$CONFIG_FILE must not be readable by group or others (use chmod 0600)." >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$CONFIG_FILE"

: "${NAMECHEAP_DDNS_PASSWORD:?NAMECHEAP_DDNS_PASSWORD is required in $CONFIG_FILE}"

update_host() {
    local host=$1
    local ip=${2:-}
    local response
    local args=(
        --data-urlencode "host=$host"
        --data-urlencode 'domain=mira-gpt.org'
        --data-urlencode "password=$NAMECHEAP_DDNS_PASSWORD"
    )

    if [[ -n $ip ]]; then
        args+=(--data-urlencode "ip=$ip")
    fi

    response=$(curl --fail --silent --show-error --get "$UPDATE_URL" "${args[@]}")

    if [[ $response != *'<ErrCount>0</ErrCount>'* ]]; then
        echo "Namecheap Dynamic DNS update failed for $host.mira-gpt.org." >&2
        return 1
    fi

    echo "$host.mira-gpt.org updated successfully."
}

is_public_ipv4() {
    python3 - "$1" <<'PY'
import ipaddress
import sys

try:
    address = ipaddress.IPv4Address(sys.argv[1])
except (IndexError, ValueError):
    raise SystemExit(1)
raise SystemExit(0 if address.is_global else 1)
PY
}

case $# in
    0)
        update_host mogwai
        update_host '*.mogwai'
        ;;
    2)
        if [[ $1 != '--chico' ]] || ! is_public_ipv4 "$2"; then
            echo 'Usage: dyndns.sh [--chico PUBLIC_IPV4]' >&2
            exit 2
        fi
        update_host chico "$2"
        update_host '*.chico' "$2"
        ;;
    *)
        echo 'Usage: dyndns.sh [--chico PUBLIC_IPV4]' >&2
        exit 2
        ;;
esac
