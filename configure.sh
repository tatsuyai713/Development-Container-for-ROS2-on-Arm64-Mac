#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

CONFIG_FILE=${CONFIG_FILE:-${CONFIG_FILE_DEFAULT}}
CONFIG_SCOPE=all
usage() {
  cat <<EOF
Usage: $0 [--build|--runtime] [--config path]

Interactively create or update the container configuration file.

Options:
  --build        Configure image build settings only
  --runtime      Configure container startup settings only
  --config path  Configuration file (default: ${CONFIG_FILE_DEFAULT})
  -h, --help     Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build) CONFIG_SCOPE=build; shift ;;
    --runtime) CONFIG_SCOPE=runtime; shift ;;
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

HOST_USER=$(id -un)
HOST_UID=$(id -u)
HOST_TIMEZONE=$(detect_host_timezone)
default_name="development-container-for-ros2-on-arm64-mac-${HOST_USER}"
default_image="development-container-for-ros2-on-arm64-mac-${HOST_USER}-u24.04:1.1.0"
default_base_image="ghcr.io/tatsuyai713/webtop-kde-base-arm64-u24.04:1.1.0"

if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
fi

CONTAINER_NAME=${CONTAINER_NAME:-${default_name}}
IMAGE_NAME=${IMAGE_NAME:-${default_image}}
UBUNTU_VERSION=${UBUNTU_VERSION:-24.04}
BASE_IMAGE=${BASE_IMAGE:-${default_base_image}}
USER_LANGUAGE=${USER_LANGUAGE:-en}
KEYBOARD_LAYOUT=${KEYBOARD_LAYOUT:-us}
INSTALL_ROS2=${INSTALL_ROS2:-true}
INSTALL_DEV_TOOLS=${INSTALL_DEV_TOOLS:-true}
CONFIG_VOLUME=${CONFIG_VOLUME:-${default_name}-config}
RESOLUTION=${RESOLUTION:-1920x1080}
DPI=${DPI:-96}
STREAM_SCALE=${STREAM_SCALE:-1.0}
FRAMERATE=${FRAMERATE:-30}
TIMEZONE=${TIMEZONE:-${HOST_TIMEZONE}}
HTTP_PORT=${HTTP_PORT:-$((50000 + HOST_UID))}
HTTPS_PORT=${HTTPS_PORT:-$((60000 + HOST_UID))}
ENABLE_XRDP=${ENABLE_XRDP:-true}
RDP_PORT=${RDP_PORT:-3389}
FOXGLOVE_PORT=${FOXGLOVE_PORT:-8765}
ROSBRIDGE_PORT=${ROSBRIDGE_PORT:-9090}
CPUS=${CPUS:-4}
MEMORY=${MEMORY:-8G}
BUILD_CPUS=${BUILD_CPUS:-4}
BUILD_MEMORY=${BUILD_MEMORY:-8G}
SHM_SIZE=${SHM_SIZE:-4G}
MOUNT_HOME=${MOUNT_HOME:-true}
MOUNT_SSH=${MOUNT_SSH:-true}
SSL_DIR=${SSL_DIR:-}

prompt() {
  local variable=$1 label=$2 default_value=$3 answer
  read -r -p "${label} [${default_value}]: " answer
  printf -v "${variable}" '%s' "${answer:-${default_value}}"
}

echo "Container configuration (${CONFIG_SCOPE})"
if [[ "${CONFIG_SCOPE}" == "all" || "${CONFIG_SCOPE}" == "build" ]]; then
  previous_ubuntu_version=${UBUNTU_VERSION}
  prompt UBUNTU_VERSION "Ubuntu version (22.04/24.04)" "${UBUNTU_VERSION}"
  [[ "${UBUNTU_VERSION}" == "22.04" || "${UBUNTU_VERSION}" == "24.04" ]] || die "Ubuntu version must be 22.04 or 24.04."
  if [[ "${UBUNTU_VERSION}" != "${previous_ubuntu_version}" ]]; then
    IMAGE_NAME=${IMAGE_NAME/u${previous_ubuntu_version}/u${UBUNTU_VERSION}}
    BASE_IMAGE=${BASE_IMAGE/u${previous_ubuntu_version}/u${UBUNTU_VERSION}}
  fi
  prompt IMAGE_NAME "Image name" "${IMAGE_NAME}"
  prompt BASE_IMAGE "Base image" "${BASE_IMAGE}"
  prompt USER_LANGUAGE "Image language (en/ja)" "${USER_LANGUAGE}"
  prompt KEYBOARD_LAYOUT "Keyboard layout (us/jp)" "${KEYBOARD_LAYOUT}"
  prompt INSTALL_ROS2 "Install ROS 2 development environment (true/false)" "${INSTALL_ROS2}"
  prompt INSTALL_DEV_TOOLS "Install development tools (true/false)" "${INSTALL_DEV_TOOLS}"
  prompt BUILD_CPUS "Build virtual CPUs" "${BUILD_CPUS}"
  prompt BUILD_MEMORY "Build memory" "${BUILD_MEMORY}"
fi
if [[ "${CONFIG_SCOPE}" == "all" || "${CONFIG_SCOPE}" == "runtime" ]]; then
  prompt CONTAINER_NAME "Container name" "${CONTAINER_NAME}"
  prompt CONFIG_VOLUME "Persistent /config volume" "${CONFIG_VOLUME}"
  prompt RESOLUTION "Desktop resolution" "${RESOLUTION}"
  prompt DPI "DPI" "${DPI}"
  prompt STREAM_SCALE "Stream scale (0.25-1.0)" "${STREAM_SCALE}"
  prompt FRAMERATE "Frame rate" "${FRAMERATE}"
  prompt TIMEZONE "Timezone" "${TIMEZONE}"
  prompt HTTP_PORT "HTTP host port" "${HTTP_PORT}"
  prompt HTTPS_PORT "HTTPS host port" "${HTTPS_PORT}"
  prompt ENABLE_XRDP "Enable XRDP (true/false)" "${ENABLE_XRDP}"
  prompt RDP_PORT "RDP host port" "${RDP_PORT}"
  prompt FOXGLOVE_PORT "Foxglove host port" "${FOXGLOVE_PORT}"
  prompt ROSBRIDGE_PORT "ROS bridge host port" "${ROSBRIDGE_PORT}"
  prompt CPUS "Virtual CPUs" "${CPUS}"
  prompt MEMORY "Memory" "${MEMORY}"
  prompt SHM_SIZE "Shared memory" "${SHM_SIZE}"
  prompt MOUNT_HOME "Mount macOS home (true/false)" "${MOUNT_HOME}"
  prompt MOUNT_SSH "Mount ~/.ssh (true/false)" "${MOUNT_SSH}"
  prompt SSL_DIR "SSL directory (blank for image defaults)" "${SSL_DIR}"
fi

[[ "${RESOLUTION}" =~ ^[0-9]+x[0-9]+$ ]] || die "Resolution must look like 1920x1080."
[[ "${UBUNTU_VERSION}" == "22.04" || "${UBUNTU_VERSION}" == "24.04" ]] || die "Ubuntu version must be 22.04 or 24.04."
[[ "${USER_LANGUAGE}" == "en" || "${USER_LANGUAGE}" == "ja" ]] || die "Image language must be en or ja."
[[ "${KEYBOARD_LAYOUT}" == "us" || "${KEYBOARD_LAYOUT}" == "jp" ]] || die "Keyboard layout must be us or jp."
[[ "${INSTALL_ROS2}" == "true" || "${INSTALL_ROS2}" == "false" ]] || die "INSTALL_ROS2 must be true or false."
[[ "${INSTALL_DEV_TOOLS}" == "true" || "${INSTALL_DEV_TOOLS}" == "false" ]] || die "INSTALL_DEV_TOOLS must be true or false."
[[ "${ENABLE_XRDP}" == "true" || "${ENABLE_XRDP}" == "false" ]] || die "ENABLE_XRDP must be true or false."
[[ "${DPI}" =~ ^[0-9]+$ ]] || die "DPI must be a positive integer."
for port in "${HTTP_PORT}" "${HTTPS_PORT}" "${RDP_PORT}" "${FOXGLOVE_PORT}" "${ROSBRIDGE_PORT}"; do
  [[ "${port}" =~ ^[0-9]+$ ]] && (( 10#${port} >= 1 && 10#${port} <= 65535 )) || die "Ports must be integers from 1 to 65535."
done
awk -v value="${STREAM_SCALE}" 'BEGIN { exit !(value >= 0.25 && value <= 1.0) }' || die "Stream scale must be 0.25-1.0."

mkdir -p "$(dirname "${CONFIG_FILE}")"
write_setting() {
  printf '%s=' "$1"
  printf '%q\n' "$2"
}
{
  echo "# Generated by configure.sh for Apple container (macOS arm64 only)"
  write_setting CONTAINER_NAME "${CONTAINER_NAME}"
  write_setting IMAGE_NAME "${IMAGE_NAME}"
  write_setting UBUNTU_VERSION "${UBUNTU_VERSION}"
  write_setting BASE_IMAGE "${BASE_IMAGE}"
  write_setting USER_LANGUAGE "${USER_LANGUAGE}"
  write_setting KEYBOARD_LAYOUT "${KEYBOARD_LAYOUT}"
  write_setting INSTALL_ROS2 "${INSTALL_ROS2}"
  write_setting INSTALL_DEV_TOOLS "${INSTALL_DEV_TOOLS}"
  write_setting CONFIG_VOLUME "${CONFIG_VOLUME}"
  write_setting RESOLUTION "${RESOLUTION}"
  write_setting DPI "${DPI}"
  write_setting STREAM_SCALE "${STREAM_SCALE}"
  write_setting FRAMERATE "${FRAMERATE}"
  write_setting TIMEZONE "${TIMEZONE}"
  write_setting HTTP_PORT "${HTTP_PORT}"
  write_setting HTTPS_PORT "${HTTPS_PORT}"
  write_setting ENABLE_XRDP "${ENABLE_XRDP}"
  write_setting RDP_PORT "${RDP_PORT}"
  write_setting FOXGLOVE_PORT "${FOXGLOVE_PORT}"
  write_setting ROSBRIDGE_PORT "${ROSBRIDGE_PORT}"
  write_setting CPUS "${CPUS}"
  write_setting MEMORY "${MEMORY}"
  write_setting BUILD_CPUS "${BUILD_CPUS}"
  write_setting BUILD_MEMORY "${BUILD_MEMORY}"
  write_setting SHM_SIZE "${SHM_SIZE}"
  write_setting MOUNT_HOME "${MOUNT_HOME}"
  write_setting MOUNT_SSH "${MOUNT_SSH}"
  write_setting SSL_DIR "${SSL_DIR}"
} > "${CONFIG_FILE}"

echo "Container configuration saved: ${CONFIG_FILE}"
case "${CONFIG_SCOPE}" in
  build) echo "These settings will be used by the image build." ;;
  runtime) echo "These settings will be applied when the container is created." ;;
  all) echo "Build settings are used by ./build.sh; runtime settings are used by ./start.sh." ;;
esac
