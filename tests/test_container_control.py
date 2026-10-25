import importlib.util
import json
from pathlib import Path
import tempfile
import gzip
import hashlib
import sys
import fcntl
import unittest
import threading
import time
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('control', Path(__file__).resolve().parents[1] / 'scripts/container-control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class ControlTests(unittest.TestCase):
    def test_status_bypasses_operation_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary); locks = state / 'locks'; locks.mkdir()
            with (locks / 'test.lock').open('a') as held:
                fcntl.flock(held, fcntl.LOCK_EX)
                with patch.object(control, 'dispatch_locked', return_value={'message': 'running'}) as dispatch:
                    self.assertEqual(control.dispatch(state, 'container', 'test', 'status')['message'], 'running')
                    dispatch.assert_called_once()

    def test_save_does_not_block_status_or_queue_stop(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary); identifier = control.channel_id('test')
            control.atomic_json(state / 'registry.json', {identifier: {'container': 'test'}})
            channel = state / 'channels' / identifier
            (channel / 'requests').mkdir(parents=True); (channel / 'responses').mkdir()
            for letter, action in [('a', 'save'), ('b', 'stop'), ('c', 'status')]:
                (channel / 'requests' / (letter * 32 + '.json')).write_text(json.dumps({'action': action}))
            release = threading.Event()
            def dispatch(state, cli, identifier, action):
                if action == 'save':
                    if not release.wait(5):
                        raise RuntimeError('Test timed out waiting for release')
                elif action == 'stop':
                    raise AssertionError('Stop must not run after the save')
                return {'message': action}
            with patch.object(control, 'dispatch', side_effect=dispatch) as mocked:
                server = threading.Thread(target=control.serve, args=(state, 'container', True))
                server.start()
                try:
                    status = channel / 'responses' / ('c' * 32 + '.json')
                    deadline = time.monotonic() + 3
                    while not status.exists() and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertTrue(status.exists(), 'Status must return before Save completes')
                    self.assertTrue(json.loads(status.read_text())['ok'])
                    stop = json.loads((channel / 'responses' / ('b' * 32 + '.json')).read_text())
                    self.assertFalse(stop['ok'])
                    self.assertIn('not queued', stop['message'])
                    self.assertEqual([call.args[3] for call in mocked.call_args_list], ['save', 'status'])
                finally:
                    release.set(); server.join(5)
                self.assertFalse(server.is_alive())

    def test_duplicate_operation_is_rejected_without_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary); locks = state / 'locks'; locks.mkdir()
            with (locks / 'test.lock').open('a') as held:
                fcntl.flock(held, fcntl.LOCK_EX)
                with patch.object(control, 'dispatch_locked') as dispatch:
                    with self.assertRaisesRegex(RuntimeError, 'Another operation'):
                        control.dispatch(state, 'container', 'test', 'save')
                    dispatch.assert_not_called()

    def test_failed_delta_stream_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            layer = Path(temporary) / 'layer.gz'
            command = [sys.executable, '-c', 'import sys;sys.stdout.write("partial");sys.stderr.write("Cannot read: Input/output error");sys.exit(1)']
            with self.assertRaisesRegex(RuntimeError, 'Input/output error'):
                control.capture_layer(command, layer)

    def test_config_preserves_metadata_and_effective_command(self):
        original = {'architecture': 'arm64', 'os': 'linux', 'config': {
            'Env': ['OLD=1'], 'User': 'root', 'Labels': {'keep': 'yes'},
            'Volumes': {'/config': {}}, 'ExposedPorts': {'3000/tcp': {}},
            'Entrypoint': ['/old'], 'Cmd': ['old'], 'WorkingDir': '/old'},
            'rootfs': {'type': 'layers', 'diff_ids': ['old', 'old2']}}
        process = {'executable': '/bin/sleep', 'arguments': ['123'],
                   'environment': ['NEW=2'], 'workingDirectory': '/work',
                   'user': {'id': {'uid': 1000, 'gid': 1001}}}
        result = control.effective_config(original, {'configuration': {'initProcess': process}}, 'abc')
        self.assertEqual(result['config']['Labels'], {'keep': 'yes'})
        self.assertEqual(result['config']['Volumes'], {'/config': {}})
        self.assertEqual(result['config']['ExposedPorts'], {'3000/tcp': {}})
        self.assertEqual(result['config']['Entrypoint'], ['/bin/sleep'])
        self.assertEqual(result['config']['Cmd'], ['123'])
        self.assertEqual(result['config']['User'], '1000:1001')
        self.assertEqual(result['rootfs']['diff_ids'], ['old', 'old2', 'sha256:abc'])
        self.assertEqual(original['config']['Env'], ['OLD=1'])

    def test_request_rejects_commands_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / 'request.json'
            for request in [{'action': 'delete'}, {'action': 'stop', 'container': 'other'},
                            {'action': 'save', 'command': 'arbitrary shell'}, []]:
                p.write_text(json.dumps(request))
                with self.assertRaises((ValueError, TypeError)):
                    control.read_request(p)
            p.write_text('{"action":"status"}')
            self.assertEqual(control.read_request(p), 'status')
            link = p.with_name('link'); link.symlink_to(p)
            with self.assertRaises(OSError):
                control.read_request(link)

    def test_queue_uses_registered_target_and_returns_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary); identifier = control.channel_id('test-container')
            control.atomic_json(state / 'registry.json', {identifier: {'container': 'test-container'}})
            channel = state / 'channels' / identifier
            (channel / 'requests').mkdir(parents=True); (channel / 'responses').mkdir()
            request = channel / 'requests' / ('a' * 32 + '.json')
            request.write_text('{"action":"status"}')
            with patch.object(control, 'dispatch', return_value={'message': 'running'}) as dispatch:
                control.serve(state, 'container', once=True)
                dispatch.assert_called_once_with(state, 'container', identifier, 'status')
            result = json.loads((channel / 'responses' / request.name).read_text())
            self.assertTrue(result['ok']); self.assertFalse(request.exists())
            request.write_text('{"action":"delete"}')
            with patch.object(control, 'dispatch') as dispatch:
                control.serve(state, 'container', once=True)
                dispatch.assert_not_called()
            self.assertFalse(json.loads((channel / 'responses' / request.name).read_text())['ok'])

    def test_failed_save_does_not_change_preferred_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary); identifier = control.channel_id('test')
            record = {'container': 'test', 'base_image': 'test:base', 'saved_image': 'test:previous'}
            control.atomic_json(state / 'registry.json', {identifier: record})
            with patch.object(control, 'inspect_container', return_value={}), patch.object(control, 'save_image', side_effect=RuntimeError('export failed')):
                with self.assertRaises(RuntimeError):
                    control.dispatch(state, 'container', identifier, 'save')
            self.assertEqual(control.registry(state)[identifier]['saved_image'], 'test:previous')

    def test_stop_retains_container(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary); identifier = control.channel_id('test')
            control.atomic_json(state / 'registry.json', {identifier: {'container': 'test'}})
            with patch.object(control, 'inspect_container', return_value={'status': {'state': 'running'}}), patch.object(control, 'run') as run:
                control.dispatch(state, 'container', identifier, 'stop')
                run.assert_called_once_with('container', 'stop', 'test')


if __name__ == '__main__':
    unittest.main()
