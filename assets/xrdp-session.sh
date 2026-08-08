#!/bin/sh
unset DBUS_SESSION_BUS_ADDRESS
unset SESSION_MANAGER
export XDG_CURRENT_DESKTOP=KDE
export XDG_SESSION_DESKTOP=KDE
export DESKTOP_SESSION=plasma

xrdp_pulse_loader=/usr/libexec/pulseaudio-module-xrdp/load_pa_modules.sh
if [ -x "${xrdp_pulse_loader}" ]; then
  previous_sink=$(pactl get-default-sink 2>/dev/null || printf '%s' output)
  previous_source=$(pactl get-default-source 2>/dev/null || printf '%s' output.monitor)
  "${xrdp_pulse_loader}"
  export PULSE_SINK=xrdp-sink
  export PULSE_SOURCE=xrdp-source
  pactl set-default-sink "${previous_sink}" 2>/dev/null || true
  pactl set-default-source "${previous_source}" 2>/dev/null || true
fi

exec dbus-run-session -- startplasma-x11
