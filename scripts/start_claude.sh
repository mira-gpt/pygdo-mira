#!/usr/bin/env bash
set -euo pipefail

pygdo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="${pygdo_root}${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m gdo.mira.scripts.start_claude
