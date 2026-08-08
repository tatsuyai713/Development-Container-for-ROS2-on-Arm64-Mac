#!/usr/bin/env bash
set -euo pipefail

: "${UBUNTU_VERSION:?}"

output_dir=${XRDP_PULSEAUDIO_OUTPUT_DIR:-/xrdp-pulseaudio-root}
install -d "${output_dir}"

# Ubuntu 24.04 uses pipewire-module-xrdp from the Ubuntu repository.
[[ "${UBUNTU_VERSION}" == "22.04" ]] || exit 0

# Keep the implementation used by the original 22.04 branch, but build it in
# a throw-away image stage so compiler and development packages do not remain
# in the final image.
pulseaudio_tag=v15.99.1
xrdp_audio_tag=v0.8
work_dir=$(mktemp -d)
trap 'rm -rf "${work_dir}"' EXIT

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install --no-install-recommends -y \
  autoconf automake bison build-essential check doxygen dpkg-dev flex gettext git \
  libcap-dev libltdl-dev libpam0g-dev libpulse-dev libsndfile1-dev libssl-dev \
  libtdb-dev libtool libxml-parser-perl libxml2-dev libx11-dev libxfixes-dev \
  libxrandr-dev libxtst-dev meson nasm ninja-build pkg-config xsltproc

git clone --depth 1 --branch "${pulseaudio_tag}" --recursive \
  https://github.com/pulseaudio/pulseaudio.git "${work_dir}/pulseaudio"
meson setup "${work_dir}/pulseaudio/build" "${work_dir}/pulseaudio"
ninja -C "${work_dir}/pulseaudio/build"

git clone --depth 1 --branch "${xrdp_audio_tag}" \
  https://github.com/neutrinolabs/pulseaudio-module-xrdp.git \
  "${work_dir}/pulseaudio-module-xrdp"
cd "${work_dir}/pulseaudio-module-xrdp"
./bootstrap
./configure PULSE_DIR="${work_dir}/pulseaudio"
make -j"$(nproc)"
make DESTDIR="${output_dir}" install

# The module's generic XDG autostart entry changes the server-wide default
# sink. The XRDP session launcher loads it instead, then keeps browser audio on
# the Selkies output sink while giving RDP applications a per-session sink.
rm -f "${output_dir}/etc/xdg/autostart/pulseaudio-xrdp.desktop"

find "${output_dir}" -type f \
  \( -name 'module-xrdp-sink.so' -o -name 'module-xrdp-source.so' \) \
  | grep -q .
