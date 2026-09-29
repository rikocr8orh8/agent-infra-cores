# SPDX-License-Identifier: MIT
import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from core import Inbox, signature

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.key = b'k' * 32; self.body = b'{"kind":"order.created"}'
        self.inbox = Inbox(Path(self.tmp.name)/'db', self.key, lambda:1000)
    def send(self, name='evt_1', body=None, time=1000):
        body = self.body if body is None else body
        return self.inbox.accept(name,time,body,signature(self.key,time,name,body))
    def test_accept_deduplicate_and_process(self):
        self.assertFalse(self.send()['duplicate']); self.assertTrue(self.send()['duplicate'])
        self.assertEqual(len(self.inbox.pending()),1)
        self.assertTrue(self.inbox.mark_processed('evt_1')); self.assertFalse(self.inbox.mark_processed('evt_1'))
        self.assertEqual(self.inbox.pending(),[])
    def test_signature_and_replay_window(self):
        with self.assertRaises(ValueError): self.inbox.accept('evt_1',1000,b'{}',signature(self.key,1000,'evt_1',self.body))
        with self.assertRaises(ValueError): self.send(time=699)
        with self.assertRaises(ValueError): self.send(time=1301)
        self.assertEqual(self.inbox.pending(),[])
    def test_event_identity_conflict(self):
        self.send()
        with self.assertRaises(ValueError): self.send(body=b'{"other":true}')
    def test_invalid_json_and_limits(self):
        for body in (b'[]',b'{',b'a'*1048577):
            with self.assertRaises(ValueError): self.send(body=body)
        with self.assertRaises(ValueError): self.send(name='line\nbreak')
    def test_concurrent_delivery(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda _:self.send(),range(6)))
        self.assertEqual(sum(not r['duplicate'] for r in results),1)

if __name__=='__main__': unittest.main()
