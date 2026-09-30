# SPDX-License-Identifier: MIT
import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from core import Ledger

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.ledger=Ledger(Path(self.tmp.name)/'db'); self.ledger.configure('a','period-1',100)
    def test_reserve_settle_and_replay(self):
        self.ledger.reserve('a','period-1','r1',80); self.assertTrue(self.ledger.reserve('a','period-1','r1',80)['duplicate'])
        self.assertEqual(self.ledger.balance('a','period-1')['available'],20)
        self.ledger.settle('a','period-1','r1',60); self.assertTrue(self.ledger.settle('a','period-1','r1',60)['duplicate'])
        self.assertEqual(self.ledger.balance('a','period-1'),{'cap':100,'spent':60,'held':0,'available':40})
    def test_conflict_cancel_and_cross_account(self):
        self.ledger.reserve('a','period-1','r1',80)
        with self.assertRaises(ValueError): self.ledger.reserve('a','period-1','r1',90)
        with self.assertRaises(ValueError): self.ledger.settle('b','period-1','r1',50)
        self.ledger.settle('a','period-1','r1')
        with self.assertRaises(ValueError): self.ledger.settle('a','period-1','r1',50)
        self.assertEqual(self.ledger.balance('a','period-1')['available'],100)
    def test_reserving_a_finalized_key_raises_instead_of_looking_granted(self):
        self.ledger.reserve('a','period-1','r1',10); self.ledger.settle('a','period-1','r1',5)
        with self.assertRaises(ValueError): self.ledger.reserve('a','period-1','r1',10)
        self.ledger.reserve('a','period-1','r2',10); self.ledger.settle('a','period-1','r2')
        with self.assertRaises(ValueError): self.ledger.reserve('a','period-1','r2',10)
        self.assertEqual(self.ledger.balance('a','period-1'),{'cap':100,'spent':5,'held':0,'available':95})
    def test_overage_stays_held(self):
        self.ledger.reserve('a','period-1','r1',80)
        with self.assertRaises(ValueError): self.ledger.settle('a','period-1','r1',81)
        self.assertEqual(self.ledger.balance('a','period-1')['held'],80)
        with self.assertRaises(ValueError): self.ledger.configure('a','period-1',79)
    def test_integer_validation(self):
        for amount in (True,1.5,-1,0,10**13):
            with self.assertRaises(ValueError): self.ledger.reserve('a','period-1','r1',amount)
    def test_concurrent_reservations_respect_cap(self):
        def reserve(i):
            try: self.ledger.reserve('a','period-1',str(i),30); return 1
            except ValueError: return 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: self.assertEqual(sum(pool.map(reserve,range(8))),3)
        self.assertEqual(self.ledger.balance('a','period-1')['held'],90)

if __name__=='__main__': unittest.main()
