#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

CONFIG_FILE=${CONFIG_FILE:-${CONFIG_FILE_DEFAULT}}
BASE_IMAGE_OVERRIDE=${BASE_IMAGE:-}
INTERACTIVE=true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      [[ $# -ge 2 ]] || die "--config requires a path."
      CONFIG_FILE=$2
      shift 2
      ;;
    --non-interactive) INTERACTIVE=false; shift ;;
    -h|--help) echo "Usage: $0 [--config path] [--non-interactive]"; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

require_apple_silicon_mac
require_container_cli
require_container_system
if [[ "${INTERACTIVE}" == "true" ]]; then
  "${SCRIPT_DIR}/configure.sh" --build --config "${CONFIG_FILE}"
else
  ensure_config "${CONFIG_FILE}"
fi
load_config "${CONFIG_FILE}"

if [[ -n "${BASE_IMAGE_OVERRIDE}" ]]; then
  BASE_IMAGE=${BASE_IMAGE_OVERRIDE}
fi
HOST_USER=$(id -un)
HOST_UID=$(id -u)
HOST_GID=$(id -g)

case "${USER_LANGUAGE}" in
  jp)
    USER_LANG_ENV=ja_JP.UTF-8
    USER_LANGUAGE_ENV=ja_JP:ja
    USER_INPUT_METHOD=fcitx
    USER_XMODIFIERS=@im=fcitx
    ;;
  en)
    USER_LANG_ENV=en_US.UTF-8
    USER_LANGUAGE_ENV=en_US:en
    USER_INPUT_METHOD=
    USER_XMODIFIERS=
    ;;
  *) die "Unsupported USER_LANGUAGE: ${USER_LANGUAGE}" ;;
esac

if [[ -z "${USER_PASSWORD:-}" ]]; then
  read -r -s -p "Password for ${HOST_USER}: " USER_PASSWORD
  echo
  read -r -s -p "Confirm password: " confirmation
  echo
  [[ "${USER_PASSWORD}" == "${confirmation}" ]] || die "Passwords do not match."
fi
[[ -n "${USER_PASSWORD}" ]] || die "Password must not be empty."
export USER_PASSWORD

echo "Pulling arm64 base image: ${BASE_IMAGE}"
container image pull --platform linux/arm64 "${BASE_IMAGE}"

build_args=(
  build
  --platform linux/arm64
  --cpus "${BUILD_CPUS}"
  --memory "${BUILD_MEMORY}"
  --file "${SCRIPT_DIR}/Containerfile"
  --tag "${IMAGE_NAME}"
  --build-arg "BASE_IMAGE=${BASE_IMAGE}"
  --build-arg "USER_NAME=${HOST_USER}"
  --build-arg "USER_UID=${HOST_UID}"
  --build-arg "USER_GID=${HOST_GID}"
  --build-arg "USER_LANGUAGE=${USER_LANGUAGE}"
  --build-arg "USER_LANG_ENV=${USER_LANG_ENV}"
  --build-arg "USER_LANGUAGE_ENV=${USER_LANGUAGE_ENV}"
  --build-arg "USER_INPUT_METHOD=${USER_INPUT_METHOD}"
  --build-arg "USER_XMODIFIERS=${USER_XMODIFIERS}"
  --build-arg "KEYBOARD_LAYOUT=${KEYBOARD_LAYOUT}"
  --build-arg "UBUNTU_VERSION=${UBUNTU_VERSION}"
  --build-arg "INSTALL_ROS2=${INSTALL_ROS2}"
  --build-arg "INSTALL_DEV_TOOLS=${INSTALL_DEV_TOOLS}"
  --secret id=user_password,env=USER_PASSWORD
)
if [[ "${NO_CACHE:-false}" == "true" ]]; then
  build_args+=(--no-cache)
fi
build_args+=("${SCRIPT_DIR}")

echo "Building ${IMAGE_NAME} for linux/arm64 (Ubuntu ${UBUNTU_VERSION}, language: ${USER_LANGUAGE})..."
container "${build_args[@]}"
unset USER_PASSWORD confirmation
echo "Built: ${IMAGE_NAME}"
