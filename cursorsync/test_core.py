# SPDX-License-Identifier: MIT
import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from core import SyncStore

def record(id='1',deleted=False): return {'id':id,'deleted':deleted,'data':{'name':'Sample'}}
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.store=SyncStore(Path(self.tmp.name)/'db')
    def test_atomic_pages_replay_and_tombstone(self):
        first=self.store.apply_page('tenant-a/orders',None,'next',[record()]); self.assertFalse(first['duplicate'])
        self.assertTrue(self.store.apply_page('tenant-a/orders',None,'next',[record()])['duplicate'])
        self.assertEqual(self.store.checkpoint('tenant-a/orders'),{'cursor':'next','done':False})
        self.store.apply_page('tenant-a/orders','next',None,[record(deleted=True)])
        self.assertEqual(self.store.records('tenant-a/orders'),{}); self.assertTrue(self.store.checkpoint('tenant-a/orders')['done'])
    def test_stale_and_conflicting_pages(self):
        self.store.apply_page('a',None,'next',[record()])
        with self.assertRaises(ValueError): self.store.apply_page('a',None,'next',[record('2')])
        with self.assertRaises(ValueError): self.store.apply_page('a','wrong',None,[])
        self.assertEqual(list(self.store.records('a')),['1'])
    def test_invalid_page_and_namespace_separation(self):
        with self.assertRaises(ValueError): self.store.apply_page('a',None,'next',[record(),record()])
        self.assertEqual(self.store.records('a'),{})
        self.store.apply_page('a',None,None,[record()]); self.assertEqual(self.store.records('b'),{})
    def test_cursor_cycle(self):
        self.store.apply_page('a',None,'one',[]); self.store.apply_page('a','one','two',[])
        with self.assertRaises(ValueError): self.store.apply_page('a','two','one',[])
    def test_concurrent_page_replay(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda _:self.store.apply_page('a',None,None,[record()]),range(6)))
        self.assertEqual(sum(not r['duplicate'] for r in results),1)

if __name__=='__main__': unittest.main()
