#!/usr/bin/env bash
set -euo pipefail

[[ "$(dpkg --print-architecture)" == "arm64" ]] || {
  echo "Google Chrome installation requires arm64." >&2
  exit 1
}

work_dir=$(mktemp -d)
trap 'rm -rf "${work_dir}"' EXIT
package="${work_dir}/google-chrome-stable_arm64.deb"
curl -fL --retry 3 \
  https://dl.google.com/linux/direct/google-chrome-stable_current_arm64.deb \
  -o "${package}"
[[ "$(dpkg-deb -f "${package}" Package)" == "google-chrome-stable" && \
   "$(dpkg-deb -f "${package}" Architecture)" == "arm64" ]] || {
  echo "Unexpected Google Chrome package name or architecture." >&2
  exit 1
}

# Allow apt's unprivileged download user to read the local package.
chmod 755 "${work_dir}"
chmod 644 "${package}"
DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y "${package}"
google-chrome-stable --version
