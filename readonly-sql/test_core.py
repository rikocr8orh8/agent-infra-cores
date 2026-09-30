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
    def test_tenant_reference_must_be_real_not_in_a_comment_or_string(self):
        for sql in ("SELECT id FROM orders -- :tenant_id", "SELECT id FROM orders /* :tenant_id */",
                    "SELECT id FROM orders /* :tenant_id", "SELECT ':tenant_id' AS x, id FROM orders",
                    "SELECT id FROM orders WHERE 'a'=':tenant_id'", "SELECT id FROM orders WHERE tenant=':tenant_id",
                    "SELECT id AS [:tenant_id] FROM orders", "SELECT id AS `:tenant_id` FROM orders",
                    'SELECT id AS ":tenant_id" FROM orders'):
            with self.subTest(sql=sql):
                with self.assertRaises(ValueError): ReadonlyGateway(self.path,{'q':sql}).query('q','a')
        ok=ReadonlyGateway(self.path,{'q':"SELECT id FROM orders /* note */ WHERE tenant = :tenant_id -- trailing"})
        self.assertEqual([r['id'] for r in ok.query('q','a')['rows']],['1','2'])
        for fine in ("SELECT id FROM orders WHERE tenant IN (:tenant_id)", "SELECT id FROM orders WHERE (tenant=:tenant_id)"):
            self.assertEqual([r['id'] for r in ReadonlyGateway(self.path,{'q':fine}).query('q','a')['rows']],['1','2'])
    def test_tenant_reference_must_be_the_exact_parameter_name(self):
        # SQLite reads ':tenant_id::x' and ':tenant_id(x)' as differently named parameters, so the caller could choose the tenant.
        for sql in ("SELECT id FROM orders WHERE tenant=:tenant_id::x", "SELECT id FROM orders WHERE tenant=:tenant_id(x)",
                    "SELECT id FROM orders WHERE tenant=:tenant_idx"):
            with self.subTest(sql=sql):
                with self.assertRaises(ValueError): ReadonlyGateway(self.path,{'q':sql}).query('q','a',{'tenant_id::x':'b','tenant_id(x)':'b','tenant_idx':'b'})
    def test_oversized_integer_parameter_is_a_value_error(self):
        gateway=ReadonlyGateway(self.path,{'q':'SELECT id FROM orders WHERE tenant=:tenant_id AND CAST(id AS INTEGER)<:n'})
        with self.assertRaises(ValueError): gateway.query('q','a',{'n':2**70})
    def test_result_size_is_capped_while_reading_not_after(self):
        import tracemalloc
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE big(tenant TEXT,body TEXT)')
            db.executemany('INSERT INTO big VALUES(?,?)',[('a','x'*60000)]*300)  # about 18 MB if fully read
        gateway=ReadonlyGateway(self.path,{'q':'SELECT body FROM big WHERE tenant=:tenant_id'},max_rows=1000)
        tracemalloc.start()
        try:
            with self.assertRaises(ValueError): gateway.query('q','a')
            peak=tracemalloc.get_traced_memory()[1]
        finally: tracemalloc.stop()
        self.assertLess(peak,8_000_000,'the 1 MiB cap must stop reading early, not after buffering every row')
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
