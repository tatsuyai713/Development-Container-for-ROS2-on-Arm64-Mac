#!/usr/bin/env bash
set -euo pipefail

[[ "$(dpkg --print-architecture)" == "arm64" ]] || {
  echo "This image is arm64-only." >&2
  exit 1
}

: "${USER_NAME:?}"
: "${USER_UID:?}"
: "${USER_GID:?}"
: "${KEYBOARD_LAYOUT:?}"
: "${USER_PASSWORD_FILE:?}"
[[ -s "${USER_PASSWORD_FILE}" ]] || { echo "Password secret is empty." >&2; exit 1; }
USER_PASSWORD=$(tr -d '\r\n' < "${USER_PASSWORD_FILE}")
[[ -n "${USER_PASSWORD}" ]] || { echo "Password secret is empty." >&2; exit 1; }
[[ "${KEYBOARD_LAYOUT}" == "us" || "${KEYBOARD_LAYOUT}" == "jp" ]] || {
  echo "Unsupported keyboard layout: ${KEYBOARD_LAYOUT}" >&2
  exit 1
}

install -d -m 755 /etc/X11/xorg.conf.d
printf '%s\n' \
  'Section "InputClass"' \
  '    Identifier "project-keyboard"' \
  '    MatchIsKeyboard "on"' \
  "    Option \"XkbLayout\" \"${KEYBOARD_LAYOUT}\"" \
  'EndSection' \
  > /etc/X11/xorg.conf.d/00-keyboard.conf

if getent group "${USER_NAME}" >/dev/null; then
  groupmod -o -g "${USER_GID}" "${USER_NAME}" || true
else
  groupadd -o -g "${USER_GID}" "${USER_NAME}"
fi

if getent passwd "${USER_UID}" >/dev/null; then
  old_user=$(getent passwd "${USER_UID}" | cut -d: -f1)
  [[ "${old_user}" == "${USER_NAME}" ]] || userdel -r "${old_user}" || true
fi

for group in adm cdrom dip plugdev lpadmin lxd sudo users audio video render; do
  getent group "${group}" >/dev/null || groupadd "${group}"
done

if getent passwd "${USER_NAME}" >/dev/null; then
  usermod -o -u "${USER_UID}" -g "${USER_NAME}" -d "/home/${USER_NAME}" -s /bin/bash "${USER_NAME}"
else
  useradd -m -o -u "${USER_UID}" -g "${USER_NAME}" -d "/home/${USER_NAME}" -s /bin/bash "${USER_NAME}"
fi
usermod -aG adm,cdrom,dip,plugdev,lpadmin,lxd,sudo,users,audio,video,render "${USER_NAME}"
getent group ssl-cert >/dev/null && usermod -aG ssl-cert "${USER_NAME}"
usermod -aG "${USER_NAME}" www-data 2>/dev/null || true
printf '%s:%s\n' "${USER_NAME}" "${USER_PASSWORD}" | chpasswd

secret_salt=$(openssl rand -hex 16)
TARGET_USER="${USER_NAME}" TARGET_PW="${USER_PASSWORD}" SECRET_SALT="${secret_salt}" \
python3 -c 'import hashlib,json,os
user=os.environ["TARGET_USER"]
password=os.environ["TARGET_PW"]
salt=os.environ["SECRET_SALT"]
data={"user":user,"salt":salt,"pw_hash":hashlib.sha256((password+salt).encode()).hexdigest(),"secret":hashlib.sha256((user+password+salt).encode()).hexdigest()}
with open("/etc/web-auth.json","w") as stream: json.dump(data,stream)
os.chmod("/etc/web-auth.json",0o600)'

install -d -m 755 "/home/${USER_NAME}" "/home/${USER_NAME}/.config" "/home/${USER_NAME}/.config/autostart"
for directory in Desktop Documents Downloads Music Pictures Videos Templates Public; do
  install -d -m 755 "/home/${USER_NAME}/${directory}"
done

if [[ "${USER_LANGUAGE:-en}" == "ja" ]]; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    language-pack-ja-base language-pack-ja im-config fonts-noto-cjk \
    fonts-noto-color-emoji fcitx fcitx-mozc fcitx-config-gtk \
    fcitx-frontend-gtk3 fcitx-frontend-qt5 fcitx-module-dbus \
    fcitx-module-kimpanel fcitx-module-x11 fcitx-ui-classic kde-config-fcitx
  locale-gen ja_JP.UTF-8
  update-locale LANG=ja_JP.UTF-8 LANGUAGE=ja_JP:ja LC_ALL=ja_JP.UTF-8
  im-config -n fcitx
  printf '%s\n' \
    '[Desktop Entry]' 'Type=Application' 'Exec=fcitx -d' 'Hidden=false' \
    'X-GNOME-Autostart-enabled=true' 'Name=fcitx' \
    > "/home/${USER_NAME}/.config/autostart/fcitx-autostart.desktop"
fi

cp /tmp/kubuntu-kdeglobals "/home/${USER_NAME}/.config/kdeglobals"
cp /tmp/kubuntu-kdeglobals /defaults/kdeglobals
printf '%s\n' '[LookAndFeel]' 'LookAndFeelPackage=org.kubuntu.desktop' \
  > "/home/${USER_NAME}/.config/lookandfeelrc"
printf '%s\n' '[Theme]' 'name=org.kubuntu.desktop' \
  > "/home/${USER_NAME}/.config/ksplashrc"
printf '%s\n' \
  '[Layout]' \
  'DisplayNames=' \
  "LayoutList=${KEYBOARD_LAYOUT}" \
  'Model=pc105' \
  'Options=' \
  'ResetOldOptions=true' \
  'SwitchMode=Global' \
  'Use=true' \
  > "/home/${USER_NAME}/.config/kxkbrc"

printf '%s\n' \
  'XDG_DESKTOP_DIR="$HOME/Desktop"' \
  'XDG_DOWNLOAD_DIR="$HOME/Downloads"' \
  'XDG_DOCUMENTS_DIR="$HOME/Documents"' \
  'XDG_PICTURES_DIR="$HOME/Pictures"' \
  > "/home/${USER_NAME}/.config/user-dirs.dirs"

cp /tmp/home.desktop "/home/${USER_NAME}/Desktop/home.desktop"
cp /tmp/trash.desktop "/home/${USER_NAME}/Desktop/trash.desktop"
cp /usr/local/share/xrdp-session.sh "/home/${USER_NAME}/.xsession"
cp /etc/skel/.bashrc "/home/${USER_NAME}/.bashrc" 2>/dev/null || true
chmod 755 \
  "/home/${USER_NAME}/Desktop/home.desktop" \
  "/home/${USER_NAME}/Desktop/trash.desktop" \
  "/home/${USER_NAME}/.xsession"

if [[ -s /etc/ros-distro ]]; then
  ros_distro=$(< /etc/ros-distro)
  printf '\n%s\n' "source /opt/ros/${ros_distro}/setup.bash" >> "/home/${USER_NAME}/.bashrc"
  install -d -m 755 "/home/${USER_NAME}/ros2_ws/src"
  chown -R "${USER_UID}:${USER_GID}" "/home/${USER_NAME}/ros2_ws"
  su -s /bin/bash - "${USER_NAME}" -c 'rosdep update'
fi

sed -i 's/^%sudo.*NOPASSWD: ALL/%sudo ALL=(ALL:ALL) ALL/' /etc/sudoers || true
grep -q '^%sudo .*ALL=(ALL:ALL) ALL' /etc/sudoers || echo '%sudo ALL=(ALL:ALL) ALL' >> /etc/sudoers

chown -R "${USER_UID}:${USER_GID}" "/home/${USER_NAME}"
chmod 755 "/home/${USER_NAME}/Desktop"
apt-get clean
rm -rf /var/lib/apt/lists/* \
  /tmp/kubuntu-kdeglobals /tmp/home.desktop /tmp/trash.desktop
