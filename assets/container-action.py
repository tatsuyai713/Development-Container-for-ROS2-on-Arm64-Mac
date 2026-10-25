#!/usr/bin/env python3
"""Desktop client: submit one fixed action to this container's host channel."""
import json
import shutil
from pathlib import Path
import subprocess
import sys
import time
import uuid


def dialog(option, message, details=None, title='Container Management'):
    command = ['kdialog', option, message]
    if details is not None:
        command.append(details)
    return subprocess.run([*command, '--title', title]).returncode


class Progress:
    """Keep feedback visible until the host responds, rather than for eight seconds."""
    def __init__(self, action):
        self.title = 'Container ' + action.title()
        self.reference = []
        self.bus = shutil.which('qdbus6') or shutil.which('qdbus')
        for path in ('/usr/lib/qt5/bin/qdbus', '/usr/lib/qt6/bin/qdbus'):
            if not self.bus and Path(path).is_file():
                self.bus = path
        self.label = ('Saving the container image on the Mac.\nLarge images can take several minutes. Keep the container running.'
                      if action == 'save' else 'Waiting for the Mac to process: ' + action)

    def call(self, method, *args):
        if self.bus and self.reference:
            return subprocess.run([self.bus, *self.reference, method, *args],
                                  capture_output=True, timeout=5)

    def __enter__(self):
        if self.bus:
            result = subprocess.run(['kdialog', '--progressbar', self.label, '0',
                                     '--title', self.title],
                                    capture_output=True, text=True, timeout=10)
            reference = result.stdout.split()
            if result.returncode == 0 and len(reference) == 2:
                self.reference = reference
                self.call('showCancelButton', 'false')
        return self

    def update(self, elapsed):
        self.call('setLabelText', self.label + f'\nElapsed: {int(elapsed)} seconds')

    def __exit__(self, *args):
        try:
            self.call('close')
        except subprocess.SubprocessError:
            pass


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ''
    if action not in ('status', 'stop', 'restart', 'save'):
        raise ValueError('Unsupported action')
    config = json.loads(Path('/etc/project-container-control.json').read_text())
    channel = Path(config['channel'])
    title = 'Container ' + action.title()
    warning = {
        'stop': 'Stop this container? Its files will be retained. This desktop connection will close.',
        'restart': 'Restart this container? Reconnect your browser or RDP client afterwards.',
        'save': 'Save changes to this container as a new image layer?\n\nExisting image layers will be reused. Only added, changed, or deleted files are saved. Mounted folders and volumes are not included.\nThe new image will be used the next time this container is recreated.',
    }
    if action in warning and dialog('--yesno', warning[action], title=title) != 0:
        return
    identifier = uuid.uuid4().hex
    request = channel / 'requests' / (identifier + '.json')
    temp = request.with_suffix('.tmp')
    temp.write_text(json.dumps({'action': action}))
    temp.replace(request)
    response = channel / 'responses' / (identifier + '.json')
    start = time.monotonic()
    deadline = start + (3600 if action == 'save' else 30)
    result = None
    with Progress(action) as progress:
        next_update = start + 5
        while time.monotonic() < deadline:
            if response.exists():
                result = json.loads(response.read_text())
                response.unlink()
                break
            if time.monotonic() >= next_update:
                progress.update(time.monotonic() - start)
                next_update = time.monotonic() + 5
            time.sleep(0.5)
    if result is not None:
        message = result.get('message', '')
        if result.get('image'):
            message += '\n\nImage: ' + result['image'] + '\nArchive on Mac: ' + result['archive']
        if result.get('export_method') == 'incremental':
            message += f'\nChanged entries: {result["changed_entries"]}\nDeleted entries: {result["deleted_entries"]}\nDelta size: {result["delta_bytes"]:,} bytes'
            if 'elapsed_seconds' in result:
                message += f'\nTime: {result["elapsed_seconds"]:.1f} seconds'
        if result.get('saved_image'):
            message += '\n\nImage for next recreation: ' + result['saved_image']
        if result['ok']:
            dialog('--msgbox', message, title=title)
        elif action == 'save':
            dialog('--detailederror', 'Failed to save the container image.', message, title=title)
        else:
            dialog('--error', message, title=title)
        return
    dialog('--error', 'The Mac did not respond in time. Check the host management service before submitting another request.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        dialog('--error', 'Container management is unavailable.\n' + str(error))
        sys.exit(1)
