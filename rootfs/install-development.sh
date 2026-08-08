#!/usr/bin/env bash
set -euo pipefail

: "${UBUNTU_VERSION:?}"
: "${INSTALL_ROS2:?}"
: "${INSTALL_DEV_TOOLS:?}"

actual_ubuntu=$(. /etc/os-release && printf '%s' "${VERSION_ID}")
[[ "${actual_ubuntu}" == "${UBUNTU_VERSION}" ]] || {
  echo "Configured Ubuntu ${UBUNTU_VERSION}, but the base image is Ubuntu ${actual_ubuntu}." >&2
  exit 1
}

case "${UBUNTU_VERSION}" in
  22.04)
    ubuntu_codename=jammy
    ros_distro=humble
    ros_desktop_package=ros-humble-desktop-full
    ;;
  24.04)
    ubuntu_codename=noble
    ros_distro=jazzy
    ros_desktop_package=ros-jazzy-desktop-full
    ;;
  *) echo "Unsupported Ubuntu version: ${UBUNTU_VERSION}" >&2; exit 1 ;;
esac

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install --no-install-recommends -y \
  ca-certificates curl dbus-x11 locales openssh-server software-properties-common \
  ssl-cert xorgxrdp xrdp

if [[ "${UBUNTU_VERSION}" == "24.04" ]]; then
  apt-get install --no-install-recommends -y pipewire-module-xrdp
fi

if [[ "${INSTALL_DEV_TOOLS}" == "true" ]]; then
  apt-get install --no-install-recommends -y \
    apt-utils bash-completion build-essential clinfo cmake command-not-found emacs \
    g++ git gnupg htop iputils-ping jq less libreoffice libreoffice-style-breeze \
    lsb-release net-tools python3-numpy python3-pip python3-venv rsync \
    p7zip-full telnet tmux unzip vim wget zip
fi

if [[ "${INSTALL_ROS2}" == "true" ]]; then
  ros_apt_source_version=1.1.0
  ros_apt_source=/tmp/ros2-apt-source.deb
  curl -fL --retry 3 \
    -o "${ros_apt_source}" \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ros_apt_source_version}/ros2-apt-source_${ros_apt_source_version}.${ubuntu_codename}_all.deb"
  dpkg -i "${ros_apt_source}"
  rm -f "${ros_apt_source}"
  apt-get update
  apt-get install --no-install-recommends -y \
    "${ros_desktop_package}" ros-dev-tools \
    python3-colcon-common-extensions python3-rosdep
  rosdep init 2>/dev/null || [[ -f /etc/ros/rosdep/sources.list.d/20-default.list ]]
  printf '%s\n' "${ros_distro}" > /etc/ros-distro
  rm -f /etc/profile.d/ros2.sh
fi

install -o root -g xrdp -m 2775 -d /run/xrdp
install -o root -g xrdp -m 3777 -d /run/xrdp/sockdir
install -o root -g root -m 0755 -d /run/dbus /run/sshd
apt-get clean
rm -rf /var/lib/apt/lists/*
