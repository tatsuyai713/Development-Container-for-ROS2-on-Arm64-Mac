#!/usr/bin/env python3
"""Resume Selkies browser audio after a Chrome user gesture."""

from pathlib import Path
import re


ASSET_DIR = Path("/usr/share/selkies/web/assets")
MARKER = "__selkiesAudioResumeInstalled"
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


assets = sorted(ASSET_DIR.glob("index-*.js"))
if not assets:
    raise SystemExit(f"No Selkies JavaScript bundle found under {ASSET_DIR}")

patched_assets = [path for path in assets if patch_asset(path)]
if not patched_assets:
    raise SystemExit("Selkies audio initialization marker was not found")

for asset in patched_assets:
    print(f"Patched Selkies audio resume handling: {asset}")
