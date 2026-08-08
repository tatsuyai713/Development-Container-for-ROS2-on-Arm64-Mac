#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

RECREATE=false
RECONFIGURE=false
NON_INTERACTIVE=false
CONFIG_FILE=${CONFIG_FILE:-${CONFIG_FILE_DEFAULT}}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --recreate) RECREATE=true; shift ;;
    --reconfigure) RECONFIGURE=true; RECREATE=true; shift ;;
    --non-interactive) NON_INTERACTIVE=true; shift ;;
    --config)
      [[ $# -ge 2 ]] || die "--config requires a path."
      CONFIG_FILE=$2
      shift 2
      ;;
    -h|--help)
      cat <<EOF
Usage: $0 [--recreate | --reconfigure] [--config path] [--non-interactive]

  --recreate     Recreate the container from the saved configuration
  --reconfigure  Interactively update runtime settings, then recreate the container
  --config path  Use a different configuration file
  --non-interactive  Never prompt; fail if runtime configuration is incomplete
EOF
      exit 0
      ;;
    *) die "Unknown option: $1" ;;
  esac
done

if [[ "${RECONFIGURE}" == "true" && "${NON_INTERACTIVE}" == "true" ]]; then
  die "--reconfigure and --non-interactive cannot be used together."
fi

require_apple_silicon_mac
require_container_cli
require_container_system

RUNTIME_SETUP_REQUIRED=false
if [[ ! -f "${CONFIG_FILE}" ]]; then
  RUNTIME_SETUP_REQUIRED=true
elif ! (
  # Older configuration files have already passed through the runtime wizard.
  RUNTIME_CONFIGURED=true
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
  [[ "${RUNTIME_CONFIGURED}" == "true" ]]
); then
  RUNTIME_SETUP_REQUIRED=true
fi

if [[ "${RECONFIGURE}" == "true" || "${RUNTIME_SETUP_REQUIRED}" == "true" ]]; then
  if [[ "${NON_INTERACTIVE}" == "true" ]]; then
    die "Runtime configuration is incomplete: ${CONFIG_FILE}. Run ./configure.sh --runtime --config ${CONFIG_FILE} first."
  fi
  [[ -t 0 ]] || die "Interactive configuration requires a terminal. Run ./configure.sh --runtime --config ${CONFIG_FILE} first."
  if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "No saved configuration found; starting the first-run setup."
  elif [[ "${RUNTIME_SETUP_REQUIRED}" == "true" ]]; then
    echo "Runtime settings have not been configured; starting the first-run setup."
  fi
  "${SCRIPT_DIR}/configure.sh" --runtime --config "${CONFIG_FILE}"
  RECREATE=true
else
  ensure_config "${CONFIG_FILE}"
fi
load_config "${CONFIG_FILE}"
image_exists "${IMAGE_NAME}" || die "Image ${IMAGE_NAME} not found. Run ./build.sh first."

if container_exists "${CONTAINER_NAME}"; then
  if [[ "${RECREATE}" == "true" ]]; then
    container stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    container delete "${CONTAINER_NAME}"
  else
    echo "Starting existing container: ${CONTAINER_NAME}"
    echo "The container keeps the settings from when it was created."
    echo "To apply the saved configuration again, use: ./start.sh --recreate"
    container start "${CONTAINER_NAME}" || die "It may already be running. Use ./status.sh to check."
    exit 0
  fi
fi

volume_exists "${CONFIG_VOLUME}" || container volume create "${CONFIG_VOLUME}" >/dev/null

HOST_USER=$(id -un)
HOST_UID=$(id -u)
HOST_GID=$(id -g)
WIDTH=${RESOLUTION%x*}
HEIGHT=${RESOLUTION#*x}
SCALE_FACTOR=$(calculate_scale "${DPI}")

run_args=(
  run -d
  --name "${CONTAINER_NAME}"
  --platform linux/arm64
  --cpus "${CPUS}"
  --memory "${MEMORY}"
  --shm-size "${SHM_SIZE}"
  --publish "127.0.0.1:${HTTP_PORT}:3000"
  --publish "127.0.0.1:${HTTPS_PORT}:3001"
  --publish "127.0.0.1:${FOXGLOVE_PORT}:8765"
  --publish "127.0.0.1:${ROSBRIDGE_PORT}:9090"
  --volume "${CONFIG_VOLUME}:/config"
  --env "START_DOCKER=false"
  --env "DISPLAY=:1"
  --env "TZ=${TIMEZONE}"
  --env "DPI=${DPI}"
  --env "SCALE_FACTOR=${SCALE_FACTOR}"
  --env "FORCE_DEVICE_SCALE_FACTOR=${SCALE_FACTOR}"
  --env "CHROMIUM_FLAGS=--force-device-scale-factor=${SCALE_FACTOR}"
  --env "DISPLAY_WIDTH=${WIDTH}"
  --env "DISPLAY_HEIGHT=${HEIGHT}"
  --env "CUSTOM_RESOLUTION=${RESOLUTION}"
  --env "STREAM_SCALE=${STREAM_SCALE}"
  --env "SELKIES_FRAMERATE=${FRAMERATE}"
  --env "ENCODER=software"
  --env "GPU_VENDOR=software"
  --env "LIBGL_ALWAYS_SOFTWARE=1"
  --env "GALLIUM_DRIVER=llvmpipe"
  --env "DISABLE_ZINK=true"
  --env "USER_NAME=${HOST_USER}"
  --env "USER_UID=${HOST_UID}"
  --env "USER_GID=${HOST_GID}"
  --env "PUID=${HOST_UID}"
  --env "PGID=${HOST_GID}"
  --env "ENABLE_XRDP=${ENABLE_XRDP}"
)

if [[ "${ENABLE_XRDP}" == "true" ]]; then
  run_args+=(--publish "127.0.0.1:${RDP_PORT}:3389")
fi

if [[ "${MOUNT_HOME}" == "true" ]]; then
  run_args+=(--mount "type=bind,source=${HOME},target=/home/${HOST_USER}/host_home")
fi
if [[ "${MOUNT_SSH}" == "true" && -d "${HOME}/.ssh" ]]; then
  run_args+=(--mount "type=bind,source=${HOME}/.ssh,target=/home/${HOST_USER}/.ssh")
fi
if [[ -n "${SSL_DIR}" ]]; then
  [[ -f "${SSL_DIR}/cert.pem" && -f "${SSL_DIR}/cert.key" ]] || die "SSL_DIR must contain cert.pem and cert.key."
  run_args+=(--mount "type=bind,source=${SSL_DIR},target=/config/ssl,readonly")
fi
run_args+=("${IMAGE_NAME}")

echo "Starting ${CONTAINER_NAME} with Apple container (linux/arm64, software rendering)..."
container "${run_args[@]}"
echo "HTTP : http://127.0.0.1:${HTTP_PORT}"
echo "HTTPS: https://127.0.0.1:${HTTPS_PORT}"
if [[ "${ENABLE_XRDP}" == "true" ]]; then
  echo "RDP  : 127.0.0.1:${RDP_PORT}"
fi
echo "Foxglove: 127.0.0.1:${FOXGLOVE_PORT}"
echo "ROS bridge: 127.0.0.1:${ROSBRIDGE_PORT}"
