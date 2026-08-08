#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_apple_silicon_mac; require_container_cli; require_container_system
load_config "${CONFIG_FILE:-${CONFIG_FILE_DEFAULT}}"
exec container exec --interactive --tty "${CONTAINER_NAME}" /bin/bash
