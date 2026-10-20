#!/usr/bin/env python3
"""Keep the physical X11 output for single-screen Plasma 6 sessions."""

from pathlib import Path


def patch(path: Path) -> None:
    source = path.read_text()
    marker = "# Keep Qt and KWin on the same physical output name."
    if marker in source:
        return
    old = ('                    for display_id, layout in layouts.items():\n'
           '                        geometry = ')
    new = ('                    for display_id, layout in layouts.items():\n'
           f'                        {marker}\n'
           '                        if len(layouts) == 1:\n'
           '                            continue\n'
           '                        geometry = ')
    if source.count(old) != 1:
        raise SystemExit(f"Unsupported Selkies monitor layout code: {path}")
    patched = source.replace(old, new, 1)
    compile(patched, str(path), "exec")
    path.write_text(patched)


if __name__ == "__main__":
    if 'VERSION_ID="26.04"' in Path('/etc/os-release').read_text():
        paths = list(Path('/opt/selkies-env/lib').glob('python*/site-packages/selkies/selkies.py'))
        if len(paths) != 1:
            raise SystemExit("Expected one Selkies Python module")
        patch(paths[0])
