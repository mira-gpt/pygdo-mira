#!/usr/bin/env bash
# Update Mogwai's Namecheap Dynamic DNS record.
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

response=$(curl --fail --silent --show-error --get "$UPDATE_URL" \
    --data-urlencode 'host=mogwai' \
    --data-urlencode 'domain=mira-gpt.org' \
    --data-urlencode "password=$NAMECHEAP_DDNS_PASSWORD")

if [[ $response != *'<ErrCount>0</ErrCount>'* ]]; then
    echo 'Namecheap Dynamic DNS update failed.' >&2
    exit 1
fi

echo 'mogwai.mira-gpt.org updated successfully.'
