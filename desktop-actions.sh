#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
[[ $# -ge 1 && $# -le 2 ]] || die "Usage: $0 <running-container-name> [configured-image]"
require_apple_silicon_mac
require_container_cli
require_container_system
python3 "${SCRIPT_DIR}/scripts/container-control.py" attach "$1" "${2:-}"
