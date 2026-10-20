#!/usr/bin/env python3
"""Desktop client: submit one fixed action to this container's host channel."""
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


def dialog(option, message):
    return subprocess.run(['kdialog', option, message, '--title', 'Container Management']).returncode


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ''
    if action not in ('status', 'stop', 'restart', 'save'):
        raise ValueError('Unsupported action')
    config = json.loads(Path('/etc/project-container-control.json').read_text())
    channel = Path(config['channel'])
    warning = {
        'stop': 'Stop this container? Its files will be retained. This desktop connection will close.',
        'restart': 'Restart this container? Reconnect your browser or RDP client afterwards.',
        'save': 'Save the current container as a new single-layer image?\n\nThe existing image will be retained. Mounted folders and volumes are not included.\nThe new image will be used the next time this container is recreated.',
    }
    if action in warning and dialog('--yesno', warning[action]) != 0:
        return
    identifier = uuid.uuid4().hex
    request = channel / 'requests' / (identifier + '.json')
    temp = request.with_suffix('.tmp')
    temp.write_text(json.dumps({'action': action}))
    temp.replace(request)
    if action in ('stop', 'restart'):
        subprocess.run(['kdialog', '--passivepopup', 'Request sent to the Mac.', '5'])
        return
    if action == 'save':
        subprocess.run(['kdialog', '--passivepopup', 'Saving the container image on the Mac. This may take several minutes.', '8'])
    response = channel / 'responses' / (identifier + '.json')
    deadline = time.monotonic() + (3600 if action == 'save' else 30)
    while time.monotonic() < deadline:
        if response.exists():
            result = json.loads(response.read_text())
            response.unlink()
            message = result.get('message', '')
            if result.get('image'):
                message += '\n\nImage: ' + result['image'] + '\nArchive on Mac: ' + result['archive']
            if result.get('saved_image'):
                message += '\n\nImage for next recreation: ' + result['saved_image']
            dialog('--msgbox' if result['ok'] else '--error', message)
            return
        time.sleep(0.5)
    dialog('--error', 'The Mac did not respond in time. Check the host management service before submitting another request.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        dialog('--error', 'Container management is unavailable.\n' + str(error))
        sys.exit(1)
