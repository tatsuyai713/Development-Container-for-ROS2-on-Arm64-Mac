import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('desktop', Path(__file__).resolve().parents[1] / 'assets/container-action.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


class DesktopActionTests(unittest.TestCase):
    def check_response(self, action, result):
        with tempfile.TemporaryDirectory() as temporary:
            channel = Path(temporary)
            (channel / 'requests').mkdir(); (channel / 'responses').mkdir()
            config = channel / 'config.json'
            config.write_text(json.dumps({'channel': str(channel)}))
            response = channel / 'responses' / ('a' * 32 + '.json')
            response.write_text(json.dumps(result))
            real_path = Path
            def path(value):
                return config if value == '/etc/project-container-control.json' else real_path(value)
            with patch.object(desktop, 'Path', side_effect=path), patch.object(desktop.sys, 'argv', ['action', action]), patch.object(desktop.uuid, 'uuid4') as identifier, patch.object(desktop, 'Progress') as progress, patch.object(desktop, 'dialog', return_value=0) as dialog:
                identifier.return_value.hex = 'a' * 32
                desktop.main()
                progress.assert_called_once_with(action)
                self.assertFalse(response.exists(), 'Host acknowledgement must be consumed')
                self.assertEqual(json.loads((channel / 'requests' / response.name).read_text()), {'action': action})
                return dialog.call_args.args

    def test_stop_displays_host_busy_error(self):
        option, message = self.check_response('stop', {'ok': False, 'message': 'Another operation is running'})
        self.assertEqual(option, '--error')
        self.assertIn('Another operation', message)

    def test_save_failure_uses_reference_detailed_error_dialog(self):
        args = self.check_response('save', {'ok': False, 'message': 'Image import failed: disk full'})
        self.assertEqual(args[0], '--detailederror')
        self.assertIn('Failed to save', args[1])
        self.assertIn('disk full', args[2])

    def test_save_displays_verified_image_and_archive(self):
        option, message = self.check_response('save', {'ok': True, 'message': 'Saved', 'image': 'test:saved', 'archive': '/backup/image.oci.tar'})
        self.assertEqual(option, '--msgbox')
        self.assertIn('test:saved', message)
        self.assertIn('/backup/image.oci.tar', message)


if __name__ == '__main__':
    unittest.main()
