#!/bin/sh
unset DBUS_SESSION_BUS_ADDRESS
unset SESSION_MANAGER
export XDG_CURRENT_DESKTOP=KDE
export XDG_SESSION_DESKTOP=KDE
export DESKTOP_SESSION=plasma
export XDG_SESSION_TYPE=x11
# Allow OpenGL animations on the container's llvmpipe renderer.
export KWIN_EFFECTS_FORCE_ANIMATIONS="${KWIN_EFFECTS_FORCE_ANIMATIONS:-1}"
unset WAYLAND_DISPLAY
if [ -r /usr/local/lib/pulse-runtime.sh ]; then
  . /usr/local/lib/pulse-runtime.sh
  webtop_configure_pulse_runtime "$(id -u)"
fi

xrdp_pulse_loader=/usr/libexec/pulseaudio-module-xrdp/load_pa_modules.sh
if [ "${WEBTOP_AUDIO_BACKEND:-}" = pipewire ]; then
  export XDG_RUNTIME_DIR="/run/user/$(id -u)"
  export PIPEWIRE_REMOTE="${XDG_RUNTIME_DIR}/pipewire-0"
  xrdp_pulse_loader=/usr/libexec/pipewire-module-xrdp/load_pw_modules.sh
fi

# Plasma 6's per-session sockets must not collide with the browser desktop.
# Keep PipeWire on its canonical runtime path above.
if command -v kwriteconfig6 >/dev/null 2>&1; then
  display_number=${DISPLAY#*:}
  display_number=${display_number%%.*}
  case "${display_number}" in
    ''|*[!0-9]*) echo "Invalid XRDP display: ${DISPLAY}" >&2; exit 1 ;;
  esac
  export XDG_RUNTIME_DIR="/run/user/$(id -u)/xrdp-${display_number}"
  mkdir -p "${XDG_RUNTIME_DIR}"
  chmod 700 "${XDG_RUNTIME_DIR}"
fi
if [ -x "${xrdp_pulse_loader}" ]; then
  previous_sink=$(pactl get-default-sink 2>/dev/null || printf '%s' output)
  previous_source=$(pactl get-default-source 2>/dev/null || printf '%s' output.monitor)
  "${xrdp_pulse_loader}"
  export PULSE_SINK=xrdp-sink
  export PULSE_SOURCE=xrdp-source
  pactl set-default-sink "${previous_sink}" 2>/dev/null || true
  pactl set-default-source "${previous_source}" 2>/dev/null || true
fi

if command -v kwriteconfig6 >/dev/null 2>&1; then
  kwriteconfig6 --file startkderc --group General --key systemdBoot false
fi
exec dbus-run-session -- startplasma-x11
