import importlib.util
import io
import os
from pathlib import Path
import shutil
import stat
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('incremental', Path(__file__).resolve().parents[1] / 'scripts/incremental_save.py')
inc = importlib.util.module_from_spec(spec); spec.loader.exec_module(inc)


@unittest.skipUnless(hasattr(os, 'listxattr'), 'Guest filesystem tests run inside Linux')
class IncrementalTests(unittest.TestCase):
    def layer(self, root, before):
        after = inc.scan(root, [])
        data = io.BytesIO(); stats = inc.write_delta(root, before, after, data)
        return tarfile.open(fileobj=io.BytesIO(data.getvalue())), stats

    def test_unchanged_large_file_is_not_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'large').write_bytes(b'x'*2000000)
            before = inc.scan(root, [])
            (root/'small').write_text('change')
            layer, stats = self.layer(root,before)
            self.assertNotIn('large', layer.getnames()); self.assertIn('small',layer.getnames())
            self.assertEqual(stats['file_bytes'],6)

    def test_same_size_and_mtime_content_change_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'file'; p.write_text('one'); before=inc.scan(root,[])
            stamp=p.stat().st_mtime_ns; p.write_text('two'); os.utime(p,ns=(stamp,stamp))
            after=inc.scan(root,[],before['memo'])
            self.assertNotEqual(before['entries']['file']['sha256'],after['entries']['file']['sha256'])
            layer,_=self.layer(root,before); self.assertEqual(layer.extractfile('file').read(),b'two')

    def test_deletions_and_type_replacements_use_whiteouts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'dir').mkdir(); (root/'dir'/'child').write_text('gone')
            (root/'file').write_text('old'); before=inc.scan(root,[])
            shutil.rmtree(root/'dir'); (root/'dir').write_text('replacement')
            (root/'file').unlink(); (root/'file').mkdir(); (root/'file'/'new').write_text('new')
            layer,_=self.layer(root,before); names=layer.getnames()
            self.assertIn('.wh.dir',names); self.assertIn('.wh.file',names)
            self.assertNotIn('dir/.wh.child',names)
            self.assertEqual(layer.extractfile('dir').read(),b'replacement')
            self.assertIn('file/new',names)

    def test_symlinks_hardlinks_modes_and_xattrs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); before=inc.scan(root,[])
            (root/'a').write_text('content'); os.chmod(root/'a',0o751)
            os.link(root/'a',root/'b'); (root/'link').symlink_to('missing')
            key='user.project-test' if os.uname().sysname=='Linux' else 'com.project.test'
            os.setxattr(root/'a',key,b'value')
            layer,_=self.layer(root,before)
            self.assertEqual(layer.getmember('a').mode,0o751)
            self.assertEqual(layer.getmember('a').pax_headers['SCHILY.xattr.'+key],'value')
            self.assertTrue(layer.getmember('b').islnk()); self.assertEqual(layer.getmember('b').linkname,'a')
            self.assertTrue(layer.getmember('link').issym()); self.assertEqual(layer.getmember('link').linkname,'missing')

    def test_hardlink_to_unchanged_target_includes_target(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'a').write_text('data'); before=inc.scan(root,[])
            os.link(root/'a',root/'b'); layer,_=self.layer(root,before)
            self.assertIn('a',layer.getnames()); self.assertTrue(layer.getmember('b').islnk())

    def test_mounted_and_transient_paths_are_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'share').mkdir(); (root/'share'/'secret').write_text('host')
            (root/'shared-other').write_text('keep'); (root/'run').mkdir()
            index=inc.scan(root,['/share','/run'])
            self.assertNotIn('share',index['entries']); self.assertNotIn('run',index['entries'])
            self.assertIn('shared-other',index['entries'])

    def test_reused_scan_cache_skips_unchanged_file_reads(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'file';p.write_text('unchanged'); first=inc.scan(root,[])
            from unittest.mock import patch
            original=Path.open
            def opened(path,*a,**kw):
                if path==p: raise AssertionError('unchanged contents should not be read again')
                return original(path,*a,**kw)
            with patch.object(Path,'open',opened): second=inc.scan(root,[],first['memo'])
            self.assertEqual(first['entries'],second['entries'])


if __name__=='__main__': unittest.main()
