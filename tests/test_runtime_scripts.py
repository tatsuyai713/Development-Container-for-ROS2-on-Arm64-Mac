import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimeScripts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'; self.bin.mkdir()
        (self.root / 'configs').mkdir()
        for name in ['common', 'start', 'stop', 'restart', 'shell', 'logs', 'status', 'delete', 'build', 'configure']:
            shutil.copy2(ROOT / (name + '.sh'), self.root)
        for name in ['update-client', 'desktop-actions']:
            p = self.root / (name + '.sh'); p.write_text('#!/bin/bash\nexit 0\n'); p.chmod(0o755)
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/container-control.py').write_text(
            'import sys; from pathlib import Path\n'
            'if sys.argv[1]=="install":\n'
            ' p=Path(__file__).parent/"channel";p.mkdir(exist_ok=True);print(p)\n'
            'elif sys.argv[1]=="resolve-image":print(sys.argv[-1])\n')
        self.log = self.root / 'calls.jsonl'
        cli = self.bin / 'container'
        cli.write_text('''#!''' + sys.executable + '''
import json,os,sys
args=sys.argv[1:]
with open(os.environ['MOCK_LOG'],'a') as log: log.write(json.dumps(args)+'\\n')
if args[0]=='inspect':
 name=args[1]
 if name not in os.environ['MOCK_EXISTING'].split(','):sys.exit(1)
 running=name in os.environ['MOCK_RUNNING'].split(',')
 print(json.dumps([{'id':name,'status':{'state':'running' if running else 'stopped'}}]))
'''); cli.chmod(0o755)
        for name, body in [('uname', 'case "$1" in -s) echo Darwin;; -m) echo arm64;; esac'), ('sw_vers', 'echo 27.0.1')]:
            p = self.bin / name; p.write_text('#!/bin/bash\n' + body + '\n'); p.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'], MOCK_LOG=str(self.log),
                        MOCK_EXISTING='test-u22.04,test-u24.04,test-u26.04', MOCK_RUNNING='test-u26.04',
                        ACTIVE_CONFIG_FILE=str(self.root / 'configs/.last-used-config'))
        self.env.pop('CONFIG_FILE', None)
        for version in ['22.04', '24.04', '26.04']:
            text = (ROOT / 'configs/example.env').read_text()
            text = text.replace('24.04', version).replace('development-container-for-ros2-on-arm64-mac-u', 'test-u')
            (self.root / 'configs' / (version + '.env')).write_text(text)

    def invoke(self, script, *args, env=None, input=''):
        return subprocess.run(['/bin/bash', str(self.root / (script + '.sh')), *args], cwd=self.root,
                              env=env or self.env, input=input, text=True, capture_output=True)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_explicit_config_for_all_versions_and_runtime_commands(self):
        for version in ['22.04', '24.04', '26.04']:
            for command in ['stop', 'restart', 'shell', 'logs', 'status', 'delete']:
                with self.subTest(version=version, command=command):
                    self.log.unlink(missing_ok=True)
                    env = dict(self.env, MOCK_RUNNING='test-u' + version)
                    args = ['--config', 'configs/' + version + '.env', '--non-interactive']
                    if command == 'delete': args += ['--yes']
                    result = self.invoke(command, *args, env=env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('Using Ubuntu ' + version, result.stdout)
                    for call in self.calls():
                        if call[0] in ['stop', 'start', 'delete', 'logs', 'stats', 'exec']:
                            self.assertIn('test-u' + version, call)

    def test_no_option_selects_only_existing_26_instead_of_default_24(self):
        shutil.copy2(self.root / 'configs/24.04.env', self.root / 'configs/default.env')
        result = self.invoke('status', '--non-interactive', env=dict(self.env, MOCK_EXISTING='test-u26.04'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Using Ubuntu 26.04', result.stdout)
        self.assertIn(['stats', '--no-stream', 'test-u26.04'], self.calls())

    def test_last_started_selection_and_explicit_override(self):
        Path(self.env['ACTIVE_CONFIG_FILE']).write_text(str(self.root / 'configs/26.04.env') + '\n')
        result = self.invoke('status', '--non-interactive')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Using Ubuntu 26.04', result.stdout)
        result = self.invoke('status', '--config', 'configs/22.04.env')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Using Ubuntu 22.04', result.stdout)

    def test_ambiguous_target_never_stops_anything(self):
        result = self.invoke('stop', '--non-interactive')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--config', result.stderr)
        self.assertFalse(any(c[0] in ['stop', 'delete'] for c in self.calls()))

    def test_missing_last_target_does_not_switch_to_another_ubuntu(self):
        Path(self.env['ACTIVE_CONFIG_FILE']).write_text(str(self.root / 'configs/26.04.env') + '\n')
        result = self.invoke('stop', '--non-interactive', env=dict(self.env, MOCK_EXISTING='test-u24.04'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('test-u26.04 not found', result.stderr)
        self.assertFalse(any(c[0] == 'stop' for c in self.calls()))

    def test_environment_config_remains_supported(self):
        result = self.invoke('logs', env=dict(self.env, CONFIG_FILE='configs/26.04.env'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(['logs', '--follow', 'test-u26.04'], self.calls())

    def test_help_and_invalid_flags_do_not_touch_containers(self):
        for command in ['stop', 'restart', 'shell', 'logs', 'status', 'delete']:
            self.assertEqual(self.invoke(command, '--help').returncode, 0)
            self.assertNotEqual(self.invoke(command, '--invalid').returncode, 0)
        self.assertFalse(self.calls())

    def test_no_configs_gives_helpful_error(self):
        for p in (self.root / 'configs').glob('*.env'):p.unlink()
        result = self.invoke('status', '--non-interactive')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Configuration not found', result.stderr)

    def test_start_records_26_for_following_runtime_commands(self):
        result = self.invoke('start', '--config', 'configs/26.04.env', '--non-interactive')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('already running', result.stdout)
        remembered = Path(self.env['ACTIVE_CONFIG_FILE']).read_text().strip()
        self.assertEqual(Path(remembered).resolve(), (self.root / 'configs/26.04.env').resolve())
        result = self.invoke('status', '--non-interactive')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Using Ubuntu 26.04', result.stdout)

    def test_create_26_uses_correct_image_and_management_mount(self):
        result = self.invoke('start', '--config', 'configs/26.04.env', '--non-interactive',
                             env=dict(self.env, MOCK_EXISTING=''))
        self.assertEqual(result.returncode, 0, result.stderr)
        run = next(c for c in self.calls() if c[0] == 'run')
        self.assertEqual(run[-1], 'test-u26.04:1.1.0')
        self.assertTrue(any('target=/run/project-container-control' in arg for arg in run))

    def test_build_passes_each_ubuntu_version(self):
        for version in ['22.04', '24.04', '26.04']:
            self.log.unlink(missing_ok=True)
            result = self.invoke('build', '--config', 'configs/' + version + '.env', '--non-interactive',
                                 env=dict(self.env, USER_PASSWORD='test-only-password'))
            self.assertEqual(result.returncode, 0, result.stderr)
            build = next(c for c in self.calls() if c[0] == 'build')
            self.assertIn('UBUNTU_VERSION=' + version, build)
            self.assertIn('BASE_IMAGE=ghcr.io/tatsuyai713/webtop-kde-base-arm64-u' + version + ':1.1.0', build)

    def test_configure_generates_26_image_and_names(self):
        result = self.invoke('configure', '--build', '--config', 'configs/new.env', input='26.04\n' + '\n' * 8)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.root / 'configs/new.env').read_text()
        self.assertIn('UBUNTU_VERSION=26.04', text)
        self.assertIn('webtop-kde-base-arm64-u26.04:1.1.0', text)


if __name__ == '__main__':
    unittest.main()
