#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
runtime_options logs "$@"
load_runtime_config
container_exists "${CONTAINER_NAME}" || die "Container ${CONTAINER_NAME} not found."
exec container logs --follow "${CONTAINER_NAME}"
