# SPDX-License-Identifier: MIT
import concurrent.futures
import sqlite3
import tempfile
import unittest
from pathlib import Path
from core import Outbox

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.now=1000; self.queue=Outbox(Path(self.tmp.name)/'db',lambda:self.now,max_attempts=2)
    def test_delivery_and_duplicate_key(self):
        self.queue.enqueue('job',{'x':1}); self.queue.enqueue('job',{'x':1})
        with self.assertRaises(ValueError): self.queue.enqueue('job',{'x':2})
        job=self.queue.claim(); self.assertEqual(self.queue.finish(job['id'],job['lease']),'done')
        self.assertIsNone(self.queue.claim())
    def test_expired_worker_cannot_ack_new_lease(self):
        self.queue.enqueue('job',{}); a=self.queue.claim(1); self.now+=2; b=self.queue.claim(10)
        with self.assertRaises(ValueError): self.queue.finish(a['id'],a['lease'])
        self.assertEqual(self.queue.finish(b['id'],b['lease']),'done')
    def test_retry_backoff_and_dead_letter(self):
        self.queue.enqueue('job',{}); a=self.queue.claim()
        self.assertEqual(self.queue.finish(a['id'],a['lease'],'retry'),'queued')
        self.assertIsNone(self.queue.claim()); self.now+=2; b=self.queue.claim()
        self.assertEqual(self.queue.finish(b['id'],b['lease'],'still down'),'dead')
        self.assertIsNone(self.queue.claim())
    def test_crashed_workers_eventually_dead_letter(self):
        self.queue.enqueue('job',{}); self.queue.claim(1); self.now+=2; self.queue.claim(1); self.now+=2
        self.assertIsNone(self.queue.claim()); self.assertEqual(self.queue.inspect()[0]['state'],'dead')
    def test_single_concurrent_claim(self):
        self.queue.enqueue('job',{})
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            claimed=list(pool.map(lambda _:self.queue.claim(),range(8)))
        self.assertEqual(sum(c is not None for c in claimed),1)
    def test_business_transaction_rollback_removes_job(self):
        with self.assertRaises(RuntimeError):
            with sqlite3.connect(self.queue.path) as db:
                db.execute('CREATE TABLE business(id TEXT)')
                db.execute('BEGIN IMMEDIATE')
                db.execute("INSERT INTO business VALUES('order-1')")
                self.queue.enqueue_in(db,'job',{'order':'order-1'})
                raise RuntimeError('business update failed')
        self.assertEqual(self.queue.inspect(),[])
        with sqlite3.connect(self.queue.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM business').fetchone()[0],0)

if __name__=='__main__': unittest.main()
