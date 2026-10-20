#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

runtime_options delete "$@"
load_runtime_config

container_found=false
volume_found=false
container_exists "${CONTAINER_NAME}" && container_found=true
volume_exists "${CONFIG_VOLUME}" && volume_found=true

if [[ "${container_found}" == "false" && ( "${DELETE_VOLUME}" == "false" || "${volume_found}" == "false" ) ]]; then
  die "Container ${CONTAINER_NAME} not found."
fi

echo "Container: ${CONTAINER_NAME}"
echo "Image    : kept (${IMAGE_NAME})"
if [[ "${DELETE_VOLUME}" == "true" ]]; then
  echo "Volume   : delete (${CONFIG_VOLUME})"
else
  echo "Volume   : kept (${CONFIG_VOLUME})"
fi

if [[ "${ASSUME_YES}" != "true" ]]; then
  read -r -p "Delete the items shown above? [y/N]: " answer
  [[ "${answer}" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }
fi

if [[ "${container_found}" == "true" ]]; then
  if container_is_running "${CONTAINER_NAME}"; then
    container stop "${CONTAINER_NAME}"
  fi
  container delete "${CONTAINER_NAME}"
  echo "Deleted container: ${CONTAINER_NAME}"
fi

if [[ "${DELETE_VOLUME}" == "true" && "${volume_found}" == "true" ]]; then
  container volume delete "${CONFIG_VOLUME}"
  echo "Deleted volume: ${CONFIG_VOLUME}"
fi
