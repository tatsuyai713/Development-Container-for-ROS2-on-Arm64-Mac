#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
runtime_options stop "$@"
load_runtime_config
container_exists "${CONTAINER_NAME}" || die "Container ${CONTAINER_NAME} not found."
if container_is_running "${CONTAINER_NAME}"; then
  container stop "${CONTAINER_NAME}"
else
  echo "Container is already stopped."
fi
if [[ "${DELETE}" == "true" ]]; then
  container delete "${CONTAINER_NAME}"
fi
