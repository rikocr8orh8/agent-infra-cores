# SPDX-License-Identifier: MIT
import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from core import Capabilities

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.now=1000; self.caps=Capabilities(Path(self.tmp.name)/'db',b'k'*32,lambda:self.now)
    def token(self): return self.caps.issue('agent-a','order.read','ORD-1')
    def test_dispatch_and_replay(self):
        token=self.token(); self.assertEqual(self.caps.dispatch(token,'agent-a','order.read','ORD-1',{'order.read':lambda resource:resource}),'ORD-1')
        with self.assertRaises(ValueError): self.caps.consume(token,'agent-a','order.read','ORD-1')
    def test_scope_tamper_and_expiry(self):
        token=self.token()
        for args in [('agent-b','order.read','ORD-1'),('agent-a','order.write','ORD-1'),('agent-a','order.read','ORD-2')]:
            with self.assertRaises(ValueError): self.caps.consume(token,*args)
        with self.assertRaises(ValueError): self.caps.consume(token+'x','agent-a','order.read','ORD-1')
        self.now+=60
        with self.assertRaises(ValueError): self.caps.consume(token,'agent-a','order.read','ORD-1')
    def test_failed_handler_does_not_restore_capability(self):
        token=self.token()
        def fail(_): raise RuntimeError('timeout')
        with self.assertRaises(RuntimeError): self.caps.dispatch(token,'agent-a','order.read','ORD-1',{'order.read':fail})
        with self.assertRaises(ValueError): self.caps.consume(token,'agent-a','order.read','ORD-1')
    def test_unregistered_tool_does_not_consume(self):
        token=self.token()
        with self.assertRaises(ValueError): self.caps.dispatch(token,'agent-a','order.read','ORD-1',{})
        self.caps.consume(token,'agent-a','order.read','ORD-1')
    def test_concurrent_single_use(self):
        token=self.token()
        def attempt(_):
            try: self.caps.consume(token,'agent-a','order.read','ORD-1'); return 1
            except ValueError: return 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt,range(8))),1)

if __name__=='__main__': unittest.main()
