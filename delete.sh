#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

CONFIG_FILE=${CONFIG_FILE:-${CONFIG_FILE_DEFAULT}}
DELETE_VOLUME=false
ASSUME_YES=false

usage() {
  cat <<EOF
Usage: $0 [--volume] [--yes] [--config path]

Delete the configured container. The image and named volume are kept by default.

Options:
  --volume       Also delete the configured /config named volume
  --yes          Skip the confirmation prompt
  --config path  Use a different configuration file
  -h, --help     Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --volume) DELETE_VOLUME=true; shift ;;
    --yes) ASSUME_YES=true; shift ;;
    --config)
      [[ $# -ge 2 ]] || die "--config requires a path."
      CONFIG_FILE=$2
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

require_apple_silicon_mac
require_container_cli
require_container_system
load_config "${CONFIG_FILE}"

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
  container stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  container delete "${CONTAINER_NAME}"
  echo "Deleted container: ${CONTAINER_NAME}"
fi

if [[ "${DELETE_VOLUME}" == "true" && "${volume_found}" == "true" ]]; then
  container volume delete "${CONFIG_VOLUME}"
  echo "Deleted volume: ${CONFIG_VOLUME}"
fi
