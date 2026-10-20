#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
runtime_options restart "$@"
load_runtime_config
container_exists "${CONTAINER_NAME}" || die "Container ${CONTAINER_NAME} not found."
if container_is_running "${CONTAINER_NAME}"; then
  container stop "${CONTAINER_NAME}"
fi
container start "${CONTAINER_NAME}"
"${SCRIPT_DIR}/update-client.sh" "${CONTAINER_NAME}"
"${SCRIPT_DIR}/desktop-actions.sh" "${CONTAINER_NAME}" "${IMAGE_NAME}"
remember_runtime_config
