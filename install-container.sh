#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

VERSION="latest"
FORCE=false
START_SYSTEM=true

usage() {
  cat <<'EOF'
Usage: ./install-container.sh [--version VERSION] [--force] [--no-start]

Download and install Apple's signed container package.

Options:
  --version VERSION  Install a specific release (default: latest)
  --force            Reinstall even when container is already installed
  --no-start         Do not start the container system after installation
  -h, --help         Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      [[ $# -ge 2 ]] || die "--version requires a value."
      VERSION=$2
      shift 2
      ;;
    --force) FORCE=true; shift ;;
    --no-start) START_SYSTEM=false; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

require_apple_silicon_mac
command -v curl >/dev/null 2>&1 || die "curl is required."
command -v pkgutil >/dev/null 2>&1 || die "pkgutil is required."
command -v installer >/dev/null 2>&1 || die "installer is required."

if command -v container >/dev/null 2>&1 && [[ "${FORCE}" != "true" ]]; then
  echo "Apple container is already installed: $(container --version)"
  echo "Use --force to reinstall it."
  exit 0
fi

if [[ "${VERSION}" == "latest" ]]; then
  release_api="https://api.github.com/repos/apple/container/releases/latest"
else
  [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || die "Invalid version: ${VERSION}"
  release_api="https://api.github.com/repos/apple/container/releases/tags/${VERSION}"
fi

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/apple-container-install.XXXXXX")
trap 'rm -rf "${tmp_dir}"' EXIT
release_json="${tmp_dir}/release.json"

echo "Fetching Apple container release information..."
curl -fsSL \
  --retry 3 \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "${release_api}" -o "${release_json}" || die "Unable to fetch release information: ${release_api}"

release_version=$(sed -n 's/^[[:space:]]*"tag_name": "\([^"]*\)",*$/\1/p' "${release_json}" | head -n 1)
[[ -n "${release_version}" ]] || die "Unable to determine the release version."

package_url=""
while IFS= read -r candidate_url; do
  package_name=${candidate_url##*/}
  if [[ "${package_name}" == "container-installer-signed.pkg" || \
        "${package_name}" == "container-${release_version}-installer-signed.pkg" ]]; then
    package_url=${candidate_url}
    break
  fi
done < <(sed -n 's/^[[:space:]]*"browser_download_url": "\(https:\/\/github\.com\/apple\/container\/releases\/download\/[^"?]*-installer-signed\.pkg\)".*$/\1/p' "${release_json}")

[[ -n "${package_url}" ]] || die "Release ${release_version} has no signed installer package."
package_file="${tmp_dir}/${package_url##*/}"

echo "Downloading Apple container ${release_version}..."
curl -fL \
  --retry 3 \
  --progress-bar \
  "${package_url}" -o "${package_file}" || die "Package download failed."
[[ -s "${package_file}" ]] || die "Downloaded package is empty."

echo "Verifying the installer signature..."
signature_info=$(pkgutil --check-signature "${package_file}") || die "The package signature is invalid."
if ! grep -Fq "Developer ID Installer: Apple Inc. - Containerization (UPBK2H6LZM)" <<<"${signature_info}" ||
   ! grep -Fq "Notarization: trusted by the Apple notary service" <<<"${signature_info}"; then
  printf '%s\n' "${signature_info}" >&2
  die "The package is not signed by the expected Apple container publisher."
fi

echo "Installing Apple container ${release_version} (administrator password may be requested)..."
sudo installer -pkg "${package_file}" -target / || die "Installation failed."
hash -r
command -v container >/dev/null 2>&1 || die "Installation completed, but the container command was not found. Open a new terminal and try again."

if [[ "${START_SYSTEM}" == "true" ]]; then
  echo "Starting Apple container services..."
  container system start
fi

echo "Installed: $(container --version)"
echo "Next: ./setup.sh"
