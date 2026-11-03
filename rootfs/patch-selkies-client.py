#!/usr/bin/env python3
"""Hardware-aware AVC decoding and user-initiated Safari text clipboard."""

import hashlib
import re
from pathlib import Path

ASSETS = Path('/usr/local/share/project-selkies')
ROOTS = Path('/usr/share/selkies')
CLIPBOARD = re.compile(
    r'(?P<head>case"clipboardUpdateFromUI":.{0,650}?const '
    r'(?P<text>[$\w]+)=(?P<event>[$\w]+)\.text;)'
    r'(?P<send>[$\w]+)\((?P=text)\);break'
)
HTML_MARKER = 'project-safari-clipboard-v1'


def patch_input_handler(path: Path) -> None:
    source = path.read_text()
    # Finish updating the X11 clipboard before processing the next WebSocket
    # key event. Scheduling a background task races with the paste shortcut.
    old = 'asyncio.create_task(_write_cw())'
    if old in source:
        patched = source.replace(old, 'await _write_cw()')
        compile(patched, str(path), 'exec')
        path.write_text(patched)


def patch_stream_transport(path: Path) -> None:
    # H.264 and Opus are already compressed. Negotiating permessage-deflate
    # adds CPU work at both ends without changing media quality or frame rate.
    source = path.read_text()
    old = 'ws = web.WebSocketResponse()'
    new = 'ws = web.WebSocketResponse(compress=False)'
    if new in source:
        return
    if source.count(old) != 1:
        raise SystemExit(f'Unsupported Selkies WebSocket constructor: {path}')
    patched = source.replace(old, new, 1)
    compile(patched, str(path), 'exec')
    path.write_text(patched)


def patch_damage_encoding(path: Path) -> None:
    """Use the existing stripe protocol with resize-triggered full refresh."""
    source = path.read_text()
    if '# project-damage-encoding' in source:
        return
    replacements = {
        'ENCODER_TYPE="x264enc"':
            '# project-damage-encoding\nENCODER_TYPE="x264enc-striped"',
        'CMD_OPTS+=(--h264-streaming-mode=true)':
            'CMD_OPTS+=(--h264-streaming-mode="false|locked")',
        'echo "[svc-selkies] H.264 streaming mode enabled for low latency"':
            'echo "[svc-selkies] Changed-region H.264 encoding enabled; configured FPS retained"',
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise SystemExit(f'Unsupported Selkies encoding settings: {path}: {old}')
        source = source.replace(old, new, 1)
    path.write_text(source)


def patch_resize_refresh(path: Path) -> None:
    source = path.read_text()
    if '# project-resize-refresh' in source:
        return
    old = '                    elif message == "START_VIDEO":'
    new = '''                    elif message == "REFRESH_VIDEO":
                        # project-resize-refresh: resend every stripe after a
                        # client canvas resize, without changing desktop size.
                        refresh_id = client_display_id or "primary"
                        now = time.monotonic()
                        last = getattr(self, "_project_refresh_times", {})
                        capture = self.capture_instances.get(refresh_id, {}).get("module")
                        if capture and now - last.get(refresh_id, 0) >= 0.5:
                            last[refresh_id] = now
                            self._project_refresh_times = last
                            if hasattr(capture, "request_idr_frame"):
                                capture.request_idr_frame()
                                data_logger.info("Full repaint requested for %s", refresh_id)
                            else:
                                await self.reconfigure_displays()

''' + old
    if source.count(old) != 1:
        raise SystemExit(f'Unsupported Selkies refresh handler: {path}')
    source = source.replace(old, new, 1)
    source = source.replace('                            "START_VIDEO",',
                            '                            "START_VIDEO",\n                            "REFRESH_VIDEO",', 1)
    compile(source, str(path), 'exec')
    path.write_text(source)


def patch_display_settings(path: Path) -> None:
    """Use the configured desktop size, including in existing saved images."""
    source = path.read_text()
    marker = '# project-configured-resolution'
    if marker in source:
        return
    header, rest = source.split('\n', 1)
    settings = '''
# project-configured-resolution
# CUSTOM_RESOLUTION is provided by start.sh; let Selkies publish and lock the
# manual dimensions so browser window size and stored client settings agree.
project_resolution=${CUSTOM_RESOLUTION:-${DISPLAY_WIDTH:-1920}x${DISPLAY_HEIGHT:-1080}}
if [[ "$project_resolution" =~ ^([0-9]+)x([0-9]+)$ ]]; then
  export SELKIES_MANUAL_WIDTH="${BASH_REMATCH[1]}"
  export SELKIES_MANUAL_HEIGHT="${BASH_REMATCH[2]}"
  export SELKIES_IS_MANUAL_RESOLUTION_MODE="true|locked"
else
  echo "Invalid CUSTOM_RESOLUTION: $project_resolution" >&2
  exit 1
fi
'''
    path.write_text(header + '\n' + settings + '\n' + rest)


def patch_keyboard_assist(source: str) -> str:
    # Window capture already forwarded these events. Never inject Enter a
    # second time from the textarea's target listener, or forward IME confirm.
    pattern = (r'(?P<head>[$\w]+\.addEventListener\("keydown",(?P<event>[$\w]+)=>\{)'
               r'(?=(?P=event)\.key==="Enter".{0,100}?(?P<remote>[$\w]+)\._guac_press)')
    return re.sub(pattern, lambda m: m['head'] + 'if(' + m['event'] + '[' +
        m['remote'] + '._EVENT_MARKER]||' + m['event'] + '.isComposing||' +
        m['event'] + '.keyCode===229)return;', source)


def patch_local_scaling(source: str) -> str:
    # Keep the native manual-mode resize listeners and pointer mapping, but
    # always fit the fixed-resolution canvas/video to its parent viewport.
    def fit(match):
        body = match[0]
        if 'Applied manual style (Scaled)' not in body or 'project-local-fit' in body:
            return body
        start = body.index('{') + 1
        return body[:start] + '/*project-local-fit*/' + match[1] + '=true;' + body[start:]
    source = re.sub(
        r'function\s+[$\w]+\([$\w]+,[$\w]+,([$\w]+)\)\{.*?(?=function\s|\Z)',
        fit, source, flags=re.S)
    # Some base clients refer to a missing variable in their video-mode
    # server-settings handler. Local fitting is always enabled here.
    return re.sub(r',scaleLocallyManual\)', ',true)', source)


def patch_clipboard_receive(source: str) -> str:
    # Publish received text before calling Safari's permission-gated API.
    # Do not depend on replacing navigator.clipboard.writeText (which may be
    # read-only), or on the success-only upstream clipboardContentUpdate event.
    return re.sub(
        r'(?<![\w.])navigator\.clipboard\.writeText\(([$\w]+)\)',
        lambda m: '(window.__projectReceiveClipboard?.(' + m[1] + '),'
        'navigator.clipboard.writeText(' + m[1] + '))', source,
    ) if 'window.__projectReceiveClipboard?.(' not in source else source


def patch_root(root: Path, assets: Path = ASSETS) -> None:
    decoder = (assets / 'selkies-hardware-decoder.js').read_text()
    clipboard = (assets / 'selkies-safari-clipboard.js').read_text()
    scripts = sorted(set(root.glob('assets/*.js')) | set(root.glob('src/*.js')))
    found = False
    for path in scripts:
        source = path.read_text()
        fitted = patch_local_scaling(source)
        if fitted != source:
            path.write_text(fitted)
            source = fitted
        # The base image's Safari focus/keyboard snippet bypasses balanced
        # key tracking. Replace it with the single project keyboard owner.
        legacy = '\n// selkies-safari-keyboard-fix (selkies-core)'
        if legacy in source:
            source = source.split(legacy, 1)[0].rstrip() + '\n'
            path.write_text(source)
        if 'project-hardware-decoder-v1' in source:
            boundary = source.find('\n})();\n')
            if not source.startswith('// project-hardware-decoder-v1') or boundary < 0:
                raise SystemExit(f'Unrecognized existing decoder patch: {path}')
            updated = decoder + source[boundary + len('\n})();\n'):]
            # The injected prelude ends in a newline; preserve the separator
            # before the original bundle across subsequent patch runs.
            if not updated.startswith(decoder + '\n'):
                updated = decoder + '\n' + source[boundary + len('\n})();\n'):]
            updated = patch_keyboard_assist(patch_clipboard_receive(updated))
            if updated != source:
                path.write_text(updated)
            found = True
            continue
        if not re.search(r'new\s+VideoDecoder\s*\(', source):
            continue
        patched, count = CLIPBOARD.subn(
            lambda m: m['head'] + 'Promise.resolve(' + m['send'] + '(' + m['text'] +
            ')).then(()=>{if(' + m['event'] + '.paste===true&&window.clipboard_enabled)'
            'window.__projectPasteRemote?.()});break', source)
        if not count:
            raise SystemExit(f'Unsupported Selkies clipboard handler: {path}')
        patched = re.sub(r'new\s+VideoDecoder\s*\(', 'new globalThis.ProjectVideoDecoder(', patched)
        patched = patched.replace('VideoDecoder.isConfigSupported(', 'globalThis.ProjectVideoDecoder.isConfigSupported(')
        path.write_text(decoder + '\n' + patch_keyboard_assist(patch_clipboard_receive(patched)))
        found = True
        print(f'Patched AVC decoding and clipboard ordering: {path}')
    if not found:
        raise SystemExit(f'No Selkies VideoDecoder bundle found under {root}')

    index = root / 'index.html'
    html = index.read_text()
    # Remove all old Safari key/focus hooks. Multiple handlers can send an
    # extra Enter and then lose its release when focus moves to a control.
    def remove_old(match):
        body = match.group()
        if '// ' + HTML_MARKER in body:
            return f'<script>\n{clipboard}\n</script>'
        if re.search(r'// selkies-safari-(?:keyboard-fix|clipboard-toolbar)', body):
            return ''
        return body
    html = re.sub(r'<script\b[^>]*>.*?</script>', remove_old, html, flags=re.S)
    if HTML_MARKER not in html:
        injection = f'<script>\n{clipboard}\n</script>\n'
        # Some wish dashboard builds omit an explicit head element.
        if '</head>' in html:
            html = html.replace('</head>', injection + '</head>', 1)
        elif re.search(r'<html\b[^>]*>', html):
            html = re.sub(r'(<html\b[^>]*>)', lambda m: m[0] + '\n' + injection, html, count=1)
        else:
            raise SystemExit(f'No HTML document in {index}')
    index.write_text(html)
    # Bundles keep their upstream content-hash filenames after post-build
    # patching. Propagate version queries from core -> Vite entry -> HTML.
    referers = scripts + [index]
    for _ in range(3):
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in scripts}
        for referer in referers:
            source = referer.read_text()
            patched = source
            for name, digest in hashes.items():
                if name == referer.name:
                    continue
                patched = re.sub(
                    re.escape(name) + r'(?:\?project_client=[a-f0-9]+)?',
                    name + '?project_client=' + digest, patched)
            if patched != source:
                referer.write_text(patched)


def patch_nginx_cache(path: Path) -> None:
    source = path.read_text()
    def update(match):
        block = match[0]
        if '# project-selkies-client-cache' in block:
            return block
        return block.replace('{', '{\n    # project-selkies-client-cache\n'
            '    add_header Cache-Control "no-store, no-cache, must-revalidate" always;\n'
            '    expires off;\n    etag off;\n    if_modified_since off;', 1)
    patched = re.sub(
        r'location\s+/\s*\{[^{}]*?alias\s+/usr/share/selkies/web/;[^{}]*\}',
        update, source)
    if patched != source:
        path.write_text(patched)


def main() -> None:
    patch_display_settings(Path('/etc/s6-overlay/s6-rc.d/svc-selkies/run'))
    patch_damage_encoding(Path('/etc/s6-overlay/s6-rc.d/svc-selkies/run'))
    # s6 copies service definitions into /run at boot. Update that copy too
    # when applying the fixes to an already running container.
    runtime_service = Path('/run/service/svc-selkies/run')
    if runtime_service.exists():
        patch_display_settings(runtime_service)
        patch_damage_encoding(runtime_service)
    # The base init-nginx recreates this site before invoking this patch.
    # Revalidate the HTML as well as the versioned JavaScript bundles.
    for path in sorted({p.resolve() for folder in ('sites-available', 'sites-enabled', 'conf.d')
                        for p in (Path('/etc/nginx') / folder).glob('*') if p.is_file()}):
        patch_nginx_cache(path)
    for path in Path('/opt/selkies-env/lib').glob('python*/site-packages/selkies/input_handler.py'):
        patch_input_handler(path)
    for path in Path('/opt/selkies-env/lib').glob('python*/site-packages/selkies/selkies.py'):
        patch_stream_transport(path)
        patch_resize_refresh(path)
    roots = sorted({p.parent.resolve() for p in ROOTS.rglob('index.html')
                    if (p.parent / 'assets').is_dir() or (p.parent / 'src').is_dir()})
    if not roots:
        raise SystemExit('No Selkies dashboards found')
    for root in roots:
        patch_root(root)


if __name__ == '__main__':
    main()
