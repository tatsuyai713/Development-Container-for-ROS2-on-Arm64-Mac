#!/usr/bin/env bash
set -euo pipefail

shopt -s nullglob
candidates=(/opt/selkies-env/lib/python*/site-packages/selkies/selkies.py)
[[ ${#candidates[@]} -gt 0 ]] || {
  echo "Selkies Python module was not found." >&2
  exit 1
}

selkies_file=${candidates[0]}
client_dpi='new_dpi = sanitize_value("scaling_dpi", settings.get("scaling_dpi"))'
fixed_client_dpi='new_dpi = int(os.environ.get("DPI", "96"))'
message_dpi='dpi_value = int(dpi_value_str)'
fixed_message_dpi='dpi_value = int(os.environ.get("DPI", dpi_value_str))'

if grep -Fq "${client_dpi}" "${selkies_file}"; then
  sed -i "s|${client_dpi}|${fixed_client_dpi}|" "${selkies_file}"
fi
if grep -Fq "${message_dpi}" "${selkies_file}"; then
  sed -i "s|${message_dpi}|${fixed_message_dpi}|" "${selkies_file}"
fi

grep -Fq "${fixed_client_dpi}" "${selkies_file}"
grep -Fq "${fixed_message_dpi}" "${selkies_file}"
