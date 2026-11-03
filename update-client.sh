#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <running-container-name>" >&2
  exit 1
fi
CLIENT_CONTAINER=$1

upload() {
  container exec --interactive "${CLIENT_CONTAINER}" python3 -c '
import sys
from pathlib import Path
path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(sys.stdin.buffer.read())
' "$2" < "${SCRIPT_DIR}/$1"
}

upload rootfs/patch-selkies-client.py /usr/local/libexec/patch-selkies-client.py
upload assets/selkies-hardware-decoder.js /usr/local/share/project-selkies/selkies-hardware-decoder.js
upload assets/selkies-safari-clipboard.js /usr/local/share/project-selkies/selkies-safari-clipboard.js
upload rootfs/custom-cont-init.d/40-timezone /custom-cont-init.d/40-timezone

# Also repair existing/saved images whose system timezone is still UTC.
container exec "${CLIENT_CONTAINER}" sh -c 'chmod 755 /custom-cont-init.d/40-timezone && /custom-cont-init.d/40-timezone'

# Base images refresh the dashboard on startup. Reapply after that refresh,
# including on containers recreated from images built before these fixes.
container exec "${CLIENT_CONTAINER}" python3 -c '
from pathlib import Path
import subprocess
hook = Path("/etc/s6-overlay/s6-rc.d/init-nginx/run")
command = "python3 /usr/local/libexec/patch-selkies-client.py"
source = hook.read_text()
if command not in source.splitlines():
    hook.write_text(source.rstrip() + "\n\n" + command + "\n")
subprocess.run(["python3", "/usr/local/libexec/patch-selkies-client.py"], check=True)
if Path("/run/nginx.pid").exists():
    subprocess.run(["nginx", "-t"], check=True)
    subprocess.run(["nginx", "-s", "reload"], check=True)
'
echo "Client fixes installed: ${CLIENT_CONTAINER}"
