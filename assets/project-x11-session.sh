#!/bin/sh
unset DBUS_SESSION_BUS_ADDRESS SESSION_MANAGER WAYLAND_DISPLAY
export XDG_CURRENT_DESKTOP=KDE XDG_SESSION_DESKTOP=KDE DESKTOP_SESSION=plasma
export XDG_SESSION_TYPE=x11
# KWin otherwise suppresses animations with Mesa's CPU renderer (llvmpipe).
export KWIN_EFFECTS_FORCE_ANIMATIONS="${KWIN_EFFECTS_FORCE_ANIMATIONS:-1}"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ -r /usr/local/lib/pulse-runtime.sh ]; then
  . /usr/local/lib/pulse-runtime.sh
  webtop_configure_pulse_runtime "$(id -u)"
fi
# Containers have no systemd user manager to launch the Plasma session.
kwriteconfig6 --file startkderc --group General --key systemdBoot false
exec dbus-run-session -- startplasma-x11
