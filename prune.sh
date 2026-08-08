#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_apple_silicon_mac; require_container_cli; require_container_system
container system df
read -r -p "Remove dangling images? [y/N]: " answer
[[ "${answer}" =~ ^[Yy]$ ]] || exit 0
container image prune
container system df
