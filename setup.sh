#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_apple_silicon_mac
require_container_cli

if container system status >/dev/null 2>&1; then
  echo "Apple container services are already running."
else
  echo "Starting Apple container services..."
  container system start
fi

container system version
echo "Setup complete. Next: ./build.sh && ./start.sh"
