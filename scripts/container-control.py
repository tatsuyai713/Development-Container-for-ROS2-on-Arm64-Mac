#!/usr/bin/env python3
"""Host-side, per-container desktop actions for Apple container."""
import argparse
import copy
import datetime as dt
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

STATE = Path.home() / '.local/state/ros2-container-control'
LABEL = 'io.github.tatsuyai713.ros2-container-control'
ACTIONS = {'status', 'stop', 'restart', 'save'}


def run(*args):
    return subprocess.check_output(list(args), text=True, stderr=subprocess.PIPE)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        temp.write_text(json.dumps(value, indent=2) + '\n')
        temp.chmod(0o600)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def registry(state):
    path = state / 'registry.json'
    return json.loads(path.read_text()) if path.exists() else {}


def update_registry(state, update):
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'registry.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        records = registry(state)
        update(records)
        atomic_json(state / 'registry.json', records)


def channel_id(name):
    return hashlib.sha256(name.encode()).hexdigest()[:24]


def inspect_container(cli, name):
    records = json.loads(run(cli, 'inspect', name))
    return next(r for r in records if r['id'] == name)


def image_config(cli, reference):
    image = json.loads(run(cli, 'image', 'inspect', reference))[0]
    for variant in image['variants']:
        if variant.get('platform', {}).get('architecture') == 'arm64':
            return copy.deepcopy(variant['config'])
    raise ValueError('Image has no arm64 configuration')


def effective_config(base, record, diff_id):
    result = copy.deepcopy(base)
    process = record['configuration']['initProcess']
    config = result.setdefault('config', {})
    config['Env'] = process.get('environment', config.get('Env', []))
    config['WorkingDir'] = process.get('workingDirectory', config.get('WorkingDir', '/'))
    raw_user = process.get('user', {}).get('raw', {}).get('userString')
    if raw_user is not None:
        config['User'] = raw_user
    elif 'id' in process.get('user', {}):
        user = process['user']['id']
        config['User'] = f"{user['uid']}:{user['gid']}"
    executable = process.get('executable')
    if executable:
        arguments = list(process.get('arguments', []))
        if arguments and arguments[0] == executable:
            arguments.pop(0)
        config['Entrypoint'] = [executable]
        config['Cmd'] = arguments
    result['created'] = dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
    result['rootfs'] = {'type': 'layers', 'diff_ids': ['sha256:' + diff_id]}
    result['history'] = [{'created': result['created'], 'created_by': 'project: save single-layer container image'}]
    return result


def blob(root, value, media_type):
    data = json.dumps(value, separators=(',', ':')).encode()
    digest = hashlib.sha256(data).hexdigest()
    (root / 'blobs/sha256' / digest).write_bytes(data)
    return {'mediaType': media_type, 'digest': 'sha256:' + digest, 'size': len(data)}


def capture_layer(command, layer, allow_changed_files=False):
    diff = hashlib.sha256()
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors,
                                   env=dict(os.environ, LC_ALL='C'))
        try:
            with layer.open('wb') as output, gzip.GzipFile(fileobj=output, mode='wb', mtime=0, compresslevel=1) as compressed:
                while chunk := process.stdout.read(1024 * 1024):
                    diff.update(chunk)
                    compressed.write(chunk)
            code = process.wait()
            errors.seek(0)
            messages = errors.read().decode(errors='replace')
            # GNU tar returns 1 when a live file changes during the copy.
            # Never accept permission, read, missing-file, or other errors.
            benign_changes = bool(messages.strip()) and all(
                line.endswith(('file changed as we read it', 'socket ignored'))
                for line in messages.splitlines() if line.strip())
            if code != 0 and not (allow_changed_files and code == 1 and benign_changes):
                raise RuntimeError(messages[-4000:] or f'Export exited with status {code}')
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
                process.wait()
    return diff.hexdigest()


def guest_tar_command(cli, name):
    # Read mountpoints in the actual guest namespace, including mounts not
    # present in the saved run configuration. Preserve directory entries, but
    # exclude every mounted directory's contents and every mounted file.
    discover = '''import json,os,re
from pathlib import Path
mounts=[]
for line in Path('/proc/self/mountinfo').read_text().splitlines():
    path=re.sub(r"\\\\([0-7]{3})",lambda m:chr(int(m[1],8)),line.split()[4])
    if path!='/': mounts.append([path,os.path.isdir(path)])
print(json.dumps(mounts))'''
    mounts = json.loads(run(cli, 'exec', '--user', 'root', name, 'python3', '-c', discover))
    command = [cli, 'exec', '--user', 'root', name,
               'env', 'LC_ALL=C', 'LANG=C', 'LANGUAGE=C',
               'tar', '--create', '--file=-', '--directory=/', '--format=pax',
               '--numeric-owner', '--xattrs', '--acls', '--one-file-system', '--anchored']
    # Runtime supervision state, session sockets, and X locks belong to the
    # current boot and must not survive restoration into a new container.
    command += ['--exclude=./run/*', '--exclude=./tmp/.X*-lock',
                '--exclude=./tmp/.X11-unix/*', '--exclude=./tmp/.ICE-unix/*']
    for mount, directory in mounts:
        command.append('--exclude=.' + mount + ('/*' if directory else ''))
    return command + ['.']


def export_layer(cli, name, layer, destination):
    try:
        return capture_layer([cli, 'export', name], layer), 'container-export'
    except RuntimeError as error:
        if inspect_container(cli, name)['status']['state'] != 'running':
            raise
        atomic_json(destination / 'export-fallback.json', {'native_export_error': str(error)})
        print('Native export failed; using guest filesystem copy with mounts excluded.', flush=True)
        # capture_layer truncates the failed native export and starts a new hash.
        return capture_layer(guest_tar_command(cli, name), layer, allow_changed_files=True), 'guest-tar'


def save_image(cli, name, target, destination):
    """Export without extracting files; build a valid single-layer OCI archive."""
    record = inspect_container(cli, name)
    base = image_config(cli, record['configuration']['image']['reference'])
    destination.mkdir(parents=True, exist_ok=False)
    atomic_json(destination / 'runtime.json', record)
    archive = destination / 'image.oci.tar'
    try:
        with tempfile.TemporaryDirectory(prefix='.save-', dir=destination) as temporary:
            root = Path(temporary)
            (root / 'blobs/sha256').mkdir(parents=True)
            layer = root / 'layer.gz'
            diff, export_method = export_layer(cli, name, layer, destination)
            compressed_hash = hashlib.sha256()
            with layer.open('rb') as saved:
                while chunk := saved.read(1024 * 1024):
                    compressed_hash.update(chunk)
            digest = compressed_hash.hexdigest()
            size = layer.stat().st_size
            layer.rename(root / 'blobs/sha256' / digest)
            config = effective_config(base, record, diff)
            config_desc = blob(root, config, 'application/vnd.oci.image.config.v1+json')
            manifest = {
                'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                'config': config_desc,
                'layers': [{'mediaType': 'application/vnd.oci.image.layer.v1.tar+gzip',
                            'digest': 'sha256:' + digest, 'size': size}],
            }
            descriptor = blob(root, manifest, manifest['mediaType'])
            descriptor['platform'] = {'os': 'linux', 'architecture': 'arm64'}
            descriptor['annotations'] = {
                'io.containerd.image.name': target,
                'org.opencontainers.image.ref.name': target.rsplit(':', 1)[-1],
                'com.apple.containerization.image.name': target,
            }
            atomic_json(root / 'index.json', {'schemaVersion': 2, 'manifests': [descriptor]})
            atomic_json(root / 'oci-layout', {'imageLayoutVersion': '1.0.0'})
            with tarfile.open(archive.with_suffix('.partial'), 'w') as output:
                for path in sorted(root.rglob('*')):
                    if path.is_file():
                        output.add(path, arcname=str(path.relative_to(root)), recursive=False)
            archive.with_suffix('.partial').replace(archive)
            run(cli, 'image', 'load', '--input', str(archive))
            loaded = image_config(cli, target)
            if loaded['config'] != config['config'] or loaded['rootfs'] != config['rootfs']:
                raise RuntimeError('Saved image configuration verification failed')
        result = {'image': target, 'archive': str(archive), 'export_method': export_method}
        atomic_json(destination / 'result.json', result)
        return result
    except BaseException:
        # Keep completed exports for recovery; discard only incomplete output.
        archive.with_suffix('.partial').unlink(missing_ok=True)
        raise


def dispatch(state, cli, identifier, action):
    locks = state / 'locks'
    locks.mkdir(parents=True, exist_ok=True)
    with (locks / (identifier + '.lock')).open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another operation is running for this container. Wait for it to finish before trying again.')
        return dispatch_locked(state, cli, identifier, action)


def dispatch_locked(state, cli, identifier, action):
    records = registry(state)
    record = records[identifier]
    name = record['container']
    current = inspect_container(cli, name)
    if action == 'status':
        return {'message': f"{name}: {current['status']['state']}",
                'saved_image': record.get('saved_image'), 'last_save': record.get('last_save')}
    if action == 'stop':
        if current['status']['state'] == 'running':
            run(cli, 'stop', name)
        return {'message': 'Container stopped. Its files were retained.'}
    if action == 'restart':
        if current['status']['state'] == 'running':
            run(cli, 'stop', name)
        run(cli, 'start', name)
        return {'message': 'Container restarted. Reconnect your browser or RDP client.'}
    if action != 'save':
        raise ValueError('Unsupported action')
    stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    target = record['base_image'].rsplit(':', 1)[0] + ':saved-' + stamp
    result = save_image(cli, name, target, state / 'backups' / identifier / stamp)
    # Reread: installation of another channel may have updated the registry.
    update_registry(state, lambda records: records[identifier].update(saved_image=target, last_save=result))
    return dict(result, message='Saved and verified a single-layer image. It will be used on the next recreation.')


def read_request(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
            raise ValueError('Invalid request file')
        request = json.load(stream)
    if not isinstance(request, dict) or set(request) != {'action'} or request['action'] not in ACTIONS:
        raise ValueError('Unsupported request')
    return request['action']


def serve(state, cli, once=False):
    while True:
        for identifier in registry(state):
            if not re.fullmatch('[a-f0-9]{24}', identifier):
                continue
            channel = state / 'channels' / identifier
            requests, responses = channel / 'requests', channel / 'responses'
            if any(p.is_symlink() for p in (channel, requests, responses)):
                continue
            for path in sorted(requests.glob('*.json')):
                if not re.fullmatch('[a-f0-9]{32}\\.json', path.name):
                    continue
                claimed = path.with_suffix('.processing')
                try:
                    path.rename(claimed)
                    action = read_request(claimed)
                    result = dispatch(state, cli, identifier, action)
                    response = dict(result, ok=True)
                except Exception as error:
                    response = {'ok': False, 'message': str(error)}
                    print(f'Container action failed: {error}', file=sys.stderr, flush=True)
                atomic_json(responses / path.name, response)
                claimed.unlink(missing_ok=True)
        if once:
            return
        time.sleep(0.5)


def install(state, cli, name, image):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    identifier = channel_id(name)
    channel = state / 'channels' / identifier
    for folder in ('requests', 'responses'):
        (channel / folder).mkdir(parents=True, exist_ok=True, mode=0o700)
    def register(records):
        previous = records.get(identifier, {})
        if previous.get('base_image') != image:
            previous = {}
        records[identifier] = dict(previous, container=name, base_image=image)
    update_registry(state, register)
    import plistlib
    agent = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    agent.parent.mkdir(parents=True, exist_ok=True)
    configuration = {
        'Label': LABEL, 'ProgramArguments': [sys.executable, str(Path(__file__).resolve()),
            '--state-dir', str(state), '--container-cli', cli, 'serve'],
        'RunAtLoad': True, 'KeepAlive': True,
        'StandardOutPath': str(state / 'agent.log'), 'StandardErrorPath': str(state / 'agent.log'),
        'EnvironmentVariables': {
            'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',
            'PROJECT_CONTAINER_CONTROL_VERSION': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    }
    changed = not agent.exists() or plistlib.loads(agent.read_bytes()) != configuration
    agent.write_bytes(plistlib.dumps(configuration))
    domain = 'gui/' + str(os.getuid())
    loaded = subprocess.run(['launchctl', 'print', domain + '/' + LABEL], capture_output=True).returncode == 0
    if loaded and changed:
        subprocess.run(['launchctl', 'bootout', domain + '/' + LABEL], check=True)
        loaded = False
    if not loaded:
        subprocess.run(['launchctl', 'bootstrap', domain, str(agent)], check=True)
    return channel


def attach(state, cli, name, image):
    current = inspect_container(cli, name)
    if current['status']['state'] != 'running':
        raise ValueError('Start the container before installing desktop actions')
    previous = registry(state).get(channel_id(name), {})
    image = image or previous.get('base_image') or current['configuration']['image']['reference']
    channel = install(state, cli, name, image)
    guest_channel = None
    # A dedicated mount is used on new containers. Existing containers can
    # use their existing host-home mount without a disruptive recreation.
    for mount in sorted(current['configuration']['mounts'], key=lambda m: len(m['source']), reverse=True):
        try:
            relative = channel.relative_to(mount['source'])
        except ValueError:
            continue
        guest_channel = str(Path(mount['destination']) / relative)
        break
    if guest_channel is None:
        raise ValueError('Control channel is not mounted. Recreate this container with start.sh --recreate.')
    root = Path(__file__).resolve().parent.parent
    env = dict(item.split('=', 1) for item in current['configuration']['initProcess']['environment'] if '=' in item)
    user = env.get('USER_NAME')
    if not user or not re.fullmatch(r'[a-z_][a-z0-9_-]*[$]?', user):
        raise ValueError('Cannot determine the desktop user')
    files = [(root / 'assets/container-action.py', '/usr/local/bin/project-container-action')]
    files += [(path, f'/home/{user}/Desktop/{path.name}') for path in sorted((root / 'assets').glob('container-*.desktop'))]
    for source, destination in files:
        subprocess.run([cli, 'exec', '--interactive', name, 'python3', '-c',
            'import sys,pwd; from pathlib import Path; p=Path(sys.argv[1]); '
            'p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(sys.stdin.buffer.read()); '
            'p.chmod(0o755); u=pwd.getpwnam(sys.argv[2]); '
            'import os; os.chown(p,u.pw_uid,u.pw_gid)', destination, user], input=source.read_bytes(), check=True)
    subprocess.run([cli, 'exec', '--interactive', name, 'python3', '-c',
        'import sys; from pathlib import Path; Path("/etc/project-container-control.json").write_bytes(sys.stdin.buffer.read())'],
        input=json.dumps({'channel': guest_channel}).encode(), check=True)
    print(f'Desktop actions installed: {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=STATE)
    parser.add_argument('--container-cli', default=shutil.which('container'))
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('install')
    setup.add_argument('name'); setup.add_argument('image')
    desktop = commands.add_parser('attach')
    desktop.add_argument('name'); desktop.add_argument('image', nargs='?', default='')
    resolve = commands.add_parser('resolve-image')
    resolve.add_argument('name'); resolve.add_argument('image')
    commands.add_parser('serve').add_argument('--once', action='store_true')
    action = commands.add_parser('action')
    action.add_argument('name'); action.add_argument('action', choices=sorted(ACTIONS))
    export = commands.add_parser('save')
    export.add_argument('name'); export.add_argument('target'); export.add_argument('destination', type=Path)
    args = parser.parse_args()
    state = args.state_dir.expanduser().resolve()
    if not args.container_cli:
        parser.error('Apple container CLI was not found')
    if args.command == 'install':
        print(install(state, args.container_cli, args.name, args.image))
    elif args.command == 'attach':
        attach(state, args.container_cli, args.name, args.image)
    elif args.command == 'resolve-image':
        record = registry(state).get(channel_id(args.name), {})
        print(record.get('saved_image', args.image) if record.get('base_image') == args.image else args.image)
    elif args.command == 'serve':
        serve(state, args.container_cli, args.once)
    elif args.command == 'action':
        print(json.dumps(dispatch(state, args.container_cli, channel_id(args.name), args.action), indent=2))
    elif args.command == 'save':
        print(json.dumps(save_image(args.container_cli, args.name, args.target, args.destination), indent=2))


if __name__ == '__main__':
    main()
