#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
runtime_options status "$@"
load_runtime_config
container inspect "${CONTAINER_NAME}"
if container_is_running "${CONTAINER_NAME}"; then
  container stats --no-stream "${CONTAINER_NAME}"
fi
