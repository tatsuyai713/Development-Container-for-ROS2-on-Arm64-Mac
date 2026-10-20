#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_apple_silicon_mac
require_container_cli

"${SCRIPT_DIR}/container-service.sh" start

container system version
echo "Setup complete. Next: ./build.sh && ./start.sh"
