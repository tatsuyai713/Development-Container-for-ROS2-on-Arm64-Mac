#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: ./container-service.sh [start|stop|restart|status]

Manage Apple container services independently of project configuration.
The default action is status. Stop and restart affect all containers using
these services, including containers outside this project.
Starting the services does not start project containers; use ./start.sh next.

  start    Start services unless already running
  stop     Stop all services
  restart  Stop services, then start them again
  status   Show service status (nonzero exit status when unavailable)
  -h, --help  Show this help
EOF
}

[[ $# -le 1 ]] || die "Expected one action. Run: ./container-service.sh --help"
ACTION=${1:-status}
case "${ACTION}" in
  -h|--help) usage; exit 0 ;;
  start|stop|restart|status) ;;
  *) die "Unknown action: ${ACTION}. Run: ./container-service.sh --help" ;;
esac

require_apple_silicon_mac
require_container_cli

start_services() {
  if container system status >/dev/null 2>&1; then
    echo "Apple container services are already running."
  else
    echo "Starting Apple container services..."
    container system start
  fi
  container system status
}

stop_services() {
  echo "Stopping Apple container services (affects all containers using these services)..."
  container system stop
}

case "${ACTION}" in
  start) start_services ;;
  stop) stop_services ;;
  restart) stop_services; start_services ;;
  status) container system status ;;
esac
