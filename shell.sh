#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
runtime_options shell "$@"
load_runtime_config
container_is_running "${CONTAINER_NAME}" || die "Container is not running. Start it with ./start.sh --config ${CONFIG_FILE}"
exec container exec --interactive --tty "${CONTAINER_NAME}" /bin/bash
