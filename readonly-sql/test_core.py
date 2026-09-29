# SPDX-License-Identifier: MIT
import sqlite3
import tempfile
import unittest
from pathlib import Path
from core import ReadonlyGateway

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.path=Path(self.tmp.name)/'db'
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE orders(id TEXT,tenant TEXT)'); db.executemany('INSERT INTO orders VALUES(?,?)',[('1','a'),('2','a'),('3','b')])
        self.gateway=ReadonlyGateway(self.path,{'orders':'SELECT id FROM orders WHERE tenant=:tenant_id ORDER BY id'},max_rows=1)
    def test_tenant_binding_and_row_cap(self):
        result=self.gateway.query('orders','a'); self.assertEqual(result['rows'],[{'id':'1'}]); self.assertTrue(result['truncated'])
        self.assertEqual(self.gateway.query('orders','b')['rows'],[{'id':'3'}])
    def test_unknown_and_override(self):
        with self.assertRaises(ValueError): self.gateway.query('raw-sql','a')
        with self.assertRaises(ValueError): self.gateway.query('orders','a',{'tenant_id':'b'})
        self.assertEqual(self.gateway.query('orders',"a' OR 1=1 --")['rows'],[])
    def test_write_denied_even_in_registry(self):
        bad=ReadonlyGateway(self.path,{'delete':'DELETE FROM orders WHERE tenant=:tenant_id'})
        with self.assertRaises(ValueError): bad.query('delete','a')
        with sqlite3.connect(self.path) as db: self.assertEqual(db.execute('SELECT count(*) FROM orders').fetchone()[0],3)
    def test_function_and_step_limits(self):
        bad=ReadonlyGateway(self.path,{'bad':'SELECT randomblob(10000000) WHERE :tenant_id IS NOT NULL'})
        with self.assertRaises(ValueError): bad.query('bad','a')
        recursive=ReadonlyGateway(self.path,{'loop':'WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT sum(x) FROM n WHERE :tenant_id IS NOT NULL'},max_steps=1000)
        with self.assertRaises(ValueError): recursive.query('loop','a')

if __name__=='__main__': unittest.main()
