#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
DELETE=false
[[ "${1:-}" == "--delete" ]] && DELETE=true
require_apple_silicon_mac; require_container_cli; require_container_system
load_config "${CONFIG_FILE:-${CONFIG_FILE_DEFAULT}}"
container_exists "${CONTAINER_NAME}" || die "Container ${CONTAINER_NAME} not found."
container stop "${CONTAINER_NAME}"
if [[ "${DELETE}" == "true" ]]; then
  container delete "${CONTAINER_NAME}"
fi
