"""OCI changesets: scan metadata/content, preserve parent layers, emit only changes.

The guest side uses only Python's standard library and runs without s6 startup
when indexing a read-only parent image. Never extract guest paths on the Mac.
"""
import base64
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tarfile
import uuid

VERSION = 1
TRANSIENT = ['/proc', '/sys', '/dev', '/run', '/tmp', '/config']


def excluded(path, exclusions):
    return any(path == prefix or path.startswith(prefix + '/') for prefix in exclusions)


def atomic_index(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, separators=(',', ':')))
    temporary.replace(path)


def scan(root, exclusions, previous=None):
    root = Path(root)
    entries, memo, inodes = {}, {}, {}
    previous = previous or {}
    def visit(relative):
        path = root / relative
        info = path.lstat()
        if stat.S_ISSOCK(info.st_mode):
            return
        entry = {'mode': info.st_mode, 'uid': info.st_uid, 'gid': info.st_gid,
                 'mtime_ns': info.st_mtime_ns}
        xattrs = {}
        try:
            for key in os.listxattr(path, follow_symlinks=False):
                xattrs[key] = base64.b64encode(os.getxattr(path, key, follow_symlinks=False)).decode()
        except OSError as error:
            if error.errno not in (errno.ENOTSUP, errno.EOPNOTSUPP):
                raise
        if xattrs:
            entry['xattrs'] = xattrs
        if stat.S_ISREG(info.st_mode):
            stamp = [info.st_dev, info.st_ino, info.st_ctime_ns, info.st_mtime_ns, info.st_size]
            cached = previous.get(relative)
            if cached and cached['stamp'] == stamp:
                digest = cached['sha256']
            else:
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                digest = digest.hexdigest()
            entry.update(size=info.st_size, sha256=digest)
            memo[relative] = {'stamp': stamp, 'sha256': digest}
            if info.st_nlink > 1:
                inode = (info.st_dev, info.st_ino)
                if inode in inodes:
                    entry['hardlink'] = inodes[inode]
                else:
                    inodes[inode] = relative
        elif stat.S_ISLNK(info.st_mode):
            entry['link'] = os.readlink(path)
        elif stat.S_ISCHR(info.st_mode) or stat.S_ISBLK(info.st_mode):
            entry.update(major=os.major(info.st_rdev), minor=os.minor(info.st_rdev))
        elif not (stat.S_ISDIR(info.st_mode) or stat.S_ISFIFO(info.st_mode)):
            raise RuntimeError('Unsupported filesystem entry: ' + relative)
        entries[relative] = entry
        if stat.S_ISDIR(info.st_mode):
            for child in sorted(os.scandir(path), key=lambda child: child.name):
                name = relative + '/' + child.name if relative else child.name
                if not excluded('/' + name, exclusions):
                    visit(name)
    # Root metadata is included, but its inode is not used as a cache key.
    visit('')
    return {'version': VERSION, 'exclusions': sorted(exclusions), 'entries': entries, 'memo': memo}


def changed_paths(before, after):
    old, new = before['entries'], after['entries']
    changed = {path for path, value in new.items() if old.get(path) != value}
    # Hardlinks must reference a file included earlier in this same layer.
    for path in list(changed):
        target = new[path].get('hardlink')
        if target:
            changed.add(target)
    removed = set(old) - set(new)
    replaced = {path for path in changed if path in old and
                stat.S_IFMT(old[path]['mode']) != stat.S_IFMT(new[path]['mode'])}
    deleted = removed | replaced
    # One directory whiteout also removes all lower-layer descendants.
    deleted = {path for path in deleted if path and not any(
        str(parent) in deleted for parent in PurePosixPath(path).parents if str(parent) != '.')}
    return sorted(changed), sorted(deleted)


def write_delta(root, before, after, output):
    changed, deleted = changed_paths(before, after)
    transferred = 0
    with tarfile.open(fileobj=output, mode='w|', format=tarfile.PAX_FORMAT) as archive:
        for path in deleted:
            pure = PurePosixPath(path)
            whiteout = tarfile.TarInfo(str(pure.parent / ('.wh.' + pure.name)))
            whiteout.mode = 0; whiteout.size = 0
            archive.addfile(whiteout)
        for relative in changed:
            entry = after['entries'][relative]
            if any(part.startswith('.wh.') for part in PurePosixPath(relative).parts):
                raise RuntimeError('OCI reserves .wh. filenames: ' + relative)
            path = Path(root) / relative
            header = tarfile.TarInfo(relative or '.')
            header.mode = stat.S_IMODE(entry['mode'])
            header.uid, header.gid = entry['uid'], entry['gid']
            header.mtime = entry['mtime_ns'] / 1_000_000_000
            header.pax_headers['mtime'] = f"{entry['mtime_ns'] // 1000000000}.{entry['mtime_ns'] % 1000000000:09d}"
            for key, value in entry.get('xattrs', {}).items():
                header.pax_headers['SCHILY.xattr.' + key] = base64.b64decode(value).decode('utf-8', 'surrogateescape')
            mode = entry['mode']
            if stat.S_ISREG(mode):
                if 'hardlink' in entry:
                    header.type = tarfile.LNKTYPE; header.linkname = entry['hardlink']
                    archive.addfile(header)
                else:
                    header.size = entry['size']
                    # Recheck type/inode without following a replaced symlink.
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    with os.fdopen(fd, 'rb') as stream:
                        current = os.fstat(stream.fileno())
                        if not stat.S_ISREG(current.st_mode):
                            raise RuntimeError('File type changed while saving: ' + relative)
                        class Reader:
                            def __init__(self): self.digest = hashlib.sha256()
                            def read(self, size):
                                data = stream.read(size); self.digest.update(data); return data
                        reader = Reader()
                        archive.addfile(header, reader)
                        entry['sha256'] = reader.digest.hexdigest()
                        # A live file changed: don't reuse its scan hash next time.
                        after['memo'].pop(relative, None)
                    transferred += header.size
            elif stat.S_ISDIR(mode): header.type = tarfile.DIRTYPE; archive.addfile(header)
            elif stat.S_ISLNK(mode): header.type = tarfile.SYMTYPE; header.linkname = entry['link']; archive.addfile(header)
            elif stat.S_ISFIFO(mode): header.type = tarfile.FIFOTYPE; archive.addfile(header)
            else:
                header.type = tarfile.CHRTYPE if stat.S_ISCHR(mode) else tarfile.BLKTYPE
                header.devmajor, header.devminor = entry['major'], entry['minor']; archive.addfile(header)
    return {'changed_entries': len(changed), 'deleted_entries': len(deleted), 'file_bytes': transferred}


def guest_main():
    mode, exclusions_json, baseline, output = sys.argv[1:5]
    exclusions = json.loads(exclusions_json)
    before = json.loads(Path(baseline).read_text()) if baseline != '-' else None
    after = scan('/', exclusions, before.get('memo') if before and mode == 'delta' else None)
    if mode == 'delta':
        after['stats'] = write_delta('/', before, after, sys.stdout.buffer)
    else:
        # Baseline inode/ctime belong to a different filesystem. Never reuse them
        # to skip hashing files in the user's running container.
        after['memo'] = {}
    atomic_index(output, after)


def manifest_for(cli, reference, run):
    image = json.loads(run(cli, 'image', 'inspect', reference))[0]
    digest = next(v['digest'] for v in image['variants'] if v.get('platform', {}).get('architecture') == 'arm64')
    store = Path(os.environ.get('CONTAINER_CONTENT_STORE', str(Path.home() / 'Library/Application Support/com.apple.container/content/blobs/sha256')))
    def read(descriptor):
        value = descriptor['digest']
        if not value.startswith('sha256:') or len(value) != 71:
            raise RuntimeError('Unsupported OCI digest: ' + value)
        path = store / value[7:]
        if not path.is_file():
            raise RuntimeError('Parent image content is missing: ' + value)
        return json.loads(path.read_text())
    manifest = read({'digest': digest})
    config = read(manifest['config'])
    for descriptor in manifest['layers']:
        if not (store / descriptor['digest'][7:]).is_file():
            raise RuntimeError('Parent layer is missing; pull or restore the parent image first')
    return digest, manifest, config


def native_import(archive, state, run):
    source = Path(__file__).with_name('load-image-metadata.c')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    binary = state / 'bin' / ('load-image-metadata-' + digest)
    binary.parent.mkdir(parents=True, exist_ok=True)
    if not binary.exists():
        try:
            temporary = binary.with_name(binary.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                run('xcrun', 'clang', '-O2', '-fblocks', str(source), '-o', str(temporary))
                temporary.replace(binary)
            finally:
                temporary.unlink(missing_ok=True)
        except RuntimeError as error:
            raise RuntimeError('Incremental Save requires Apple Command Line Tools (xcode-select --install). ' + str(error)) from error
    run(str(binary), str(archive.resolve()))


def source_identity(record):
    conf = record['configuration']
    return {'creationDate': conf.get('creationDate'), 'image': conf['image']['reference']}


def make_layer(cli, name, record, parent, destination, state, channel, run, capture):
    """Return only changed tar bytes; reuse a read-only baseline index across saves."""
    # Exclude actual mounts consistently on both sides, including injected files.
    mounts = json.loads(run(cli, 'exec', '--user', 'root', name, 'python3', '-c',
        'import json,re; from pathlib import Path; print(json.dumps([re.sub(r"\\\\([0-7]{3})",lambda m:chr(int(m[1],8)),s.split()[4]) for s in Path("/proc/self/mountinfo").read_text().splitlines() if s.split()[4]!="/"]))'))
    exclusions = sorted(set(TRANSIENT + mounts))
    digest, manifest, config = manifest_for(cli, parent, run)
    key = hashlib.sha256(json.dumps([VERSION, digest, exclusions], sort_keys=True).encode()).hexdigest()
    cache = state / 'indexes' / (key + '.json')
    channel.mkdir(parents=True, exist_ok=True)
    working = channel / ('save-' + uuid.uuid4().hex)
    working.mkdir(mode=0o700)
    # The channel is already bind-mounted on the guest. Resolve its guest path
    # without granting the helper access to the entire Mac home.
    guest_channel = None
    for mount in sorted(record['configuration']['mounts'], key=lambda m: len(m['source']), reverse=True):
        try: relative = channel.relative_to(mount['source'])
        except ValueError: continue
        guest_channel = str(Path(mount['destination']) / relative); break
    if guest_channel is None:
        raise RuntimeError('Management channel is not mounted. Recreate with start.sh first.')
    source = Path(__file__).read_text()
    try:
        if not cache.exists():
            print('Indexing parent image once; subsequent saves reuse this index.', flush=True)
            helper = 'project-save-index-' + uuid.uuid4().hex[:12]
            try:
                run(cli, 'run', '--rm', '--name', helper, '--platform', 'linux/arm64',
                    '--read-only', '--cpus', '2', '--memory', '1G', '--user', 'root',
                    '--mount', 'type=bind,source=' + str(working) + ',target=/project-save-index',
                    '--entrypoint', 'python3', parent, '-B', '-c', source,
                    'scan', json.dumps(exclusions + ['/project-save-index']), '-', '/project-save-index/index.json')
            finally:
                # --rm normally handles this; cleanup is restricted to our helper.
                subprocess.run([cli, 'delete', '--force', helper], capture_output=True)
            cache.parent.mkdir(parents=True, exist_ok=True)
            baseline = json.loads((working / 'index.json').read_text())
            baseline['exclusions'] = exclusions
            atomic_index(cache, baseline)
        before = json.loads(cache.read_text())
        # A guest scan cache is reusable only for the exact same container object.
        if before.get('source_identity') != source_identity(record):
            before['memo'] = {}
        atomic_index(working / 'before.json', before)
        guest_work = str(Path(guest_channel) / working.name)
        layer = destination / 'layer.gz'
        diff = capture([cli, 'exec', '--user', 'root', name, 'python3', '-B', '-c', source,
                        'delta', json.dumps(exclusions), guest_work + '/before.json', guest_work + '/after.json'], layer)
        after = json.loads((working / 'after.json').read_text())
        after['source_identity'] = source_identity(record)
        atomic_index(destination / 'filesystem-index.json', after)
        return diff, manifest, config, after, exclusions
    finally:
        import shutil
        shutil.rmtree(working)


if __name__ == '__main__':
    guest_main()
