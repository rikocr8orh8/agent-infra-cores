# SPDX-License-Identifier: MIT
import copy
import tempfile
import unittest
from pathlib import Path
from core import seal,verify

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)/'tree'; self.root.mkdir()
        (self.root/'report.txt').write_text('Synthetic report'); self.key=b'k'*32
    def test_seal_and_verify(self):
        envelope=seal(self.root,self.key); self.assertTrue(verify(self.root,envelope,self.key)['valid'])
    def test_content_addition_and_deletion_detected(self):
        envelope=seal(self.root,self.key); (self.root/'extra.txt').write_text('extra')
        with self.assertRaises(ValueError): verify(self.root,envelope,self.key)
        (self.root/'extra.txt').unlink(); (self.root/'report.txt').write_text('Changed')
        with self.assertRaises(ValueError): verify(self.root,envelope,self.key)
        (self.root/'report.txt').unlink()
        with self.assertRaises(ValueError): verify(self.root,envelope,self.key)
    def test_signature_key_and_manifest_tampering(self):
        envelope=seal(self.root,self.key)
        with self.assertRaises(ValueError): verify(self.root,envelope,b'x'*32)
        modified=copy.deepcopy(envelope); modified['manifest']['files']={}
        with self.assertRaises(ValueError): verify(self.root,modified,self.key)
        with self.assertRaises(ValueError): verify(self.root,envelope,self.key,'another-key')
    @unittest.skipIf(hasattr(__import__('os'),'geteuid') and __import__('os').geteuid()==0,'permission bits do not restrict root')
    def test_unreadable_directory_is_an_error_not_skipped(self):
        envelope=seal(self.root,self.key); hidden=self.root/'hidden'; hidden.mkdir()
        (hidden/'payload.sh').write_text('added after sealing'); hidden.chmod(0)
        self.addCleanup(hidden.chmod,0o755)
        with self.assertRaises(ValueError): verify(self.root,envelope,self.key)
        with self.assertRaises(ValueError): seal(self.root,self.key)
    def test_directory_walk_is_bounded_before_the_file_limits_apply(self):
        import core
        for i in range(6): (self.root/f'd{i}').mkdir()
        self.addCleanup(setattr,core,'MAX_ENTRIES',core.MAX_ENTRIES)
        core.MAX_ENTRIES=5
        with self.assertRaises(ValueError): seal(self.root,self.key)
    def test_symlinks_rejected(self):
        (self.root/'link').symlink_to(self.root/'report.txt')
        with self.assertRaises(ValueError): seal(self.root,self.key)

if __name__=='__main__': unittest.main()
