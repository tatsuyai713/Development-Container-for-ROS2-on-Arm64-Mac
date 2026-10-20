#!/usr/bin/env python3
"""Resume Selkies browser audio after a Chrome user gesture."""

from pathlib import Path
import re


ASSET_ROOT = Path("/usr/share/selkies")
MARKER = "__selkiesAudioResumeInstalled"
AUDIO_INIT = "Playback AudioWorkletProcessor initialized and connected through a GainNode for volume control."
PATTERN = re.compile(
    r'(?P<gain>[A-Za-z_$][\w$]*)\.connect\('
    r'(?P<context>[A-Za-z_$][\w$]*)\.destination\),'
    r'console\.log\("Playback AudioWorkletProcessor initialized and connected '
    r'through a GainNode for volume control\."\)'
)


def patch_asset(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    if MARKER in source:
        return True

    def replacement(match: re.Match[str]) -> str:
        gain = match.group("gain")
        context = match.group("context")
        resume = (
            f'window.{MARKER}||(window.{MARKER}=()=>{{'
            f'{context}&&{context}.state==="suspended"&&'
            f'{context}.resume().catch(e=>console.error("Error resuming audio context",e))'
            f'}},window.addEventListener("pointerdown",window.{MARKER},{{capture:!0}}),'
            f'window.addEventListener("keydown",window.{MARKER},{{capture:!0}}))'
        )
        return (
            f'{gain}.connect({context}.destination),{resume},'
            'console.log("Playback AudioWorkletProcessor initialized and connected '
            'through a GainNode for volume control.")'
        )

    patched, count = PATTERN.subn(replacement, source, count=1)
    if count != 1:
        return False
    path.write_text(patched, encoding="utf-8")
    return True


def main(asset_root: Path = ASSET_ROOT) -> None:
    # Older images use web/assets/index-*.js. Newer dashboards ship both
    # assets/selkies-core-*.js and src/selkies-core.js, so inspect all bundles
    # and select by playback code rather than a particular build filename.
    assets = []
    for path in sorted(asset_root.rglob("*.js")):
        source = path.read_text(encoding="utf-8")
        if AUDIO_INIT in source or MARKER in source:
            if MARKER not in source and not PATTERN.search(source):
                raise SystemExit(f"Unsupported Selkies audio initialization in {path}")
            assets.append(path)
    if not assets:
        raise SystemExit(f"No Selkies playback JavaScript bundle found under {asset_root}")

    for asset in assets:
        if not patch_asset(asset):
            raise SystemExit(f"Unable to patch Selkies audio initialization in {asset}")
        print(f"Patched Selkies audio resume handling: {asset}")


if __name__ == "__main__":
    main()
