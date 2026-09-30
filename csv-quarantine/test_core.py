# SPDX-License-Identifier: MIT
import sqlite3
import tempfile
import unittest
from pathlib import Path
from core import inspect_csv, import_catalog, quarantine_json

HEADER=b'sku,name,price_minor,currency\n'
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.path=Path(self.tmp.name)/'db'
        self.raw=HEADER+b'SKU-1,Widget,4900,USD\n'
    def test_import_and_replay(self):
        report=inspect_csv(self.raw); self.assertFalse(import_catalog(self.path,'supplier-a',self.raw,report['source_sha256'])['duplicate'])
        self.assertTrue(import_catalog(self.path,'supplier-a',self.raw,report['source_sha256'])['duplicate'])
    def test_quarantine_and_no_partial_write(self):
        raw=self.raw+b'SKU-2,=HYPERLINK("evil"),oops,BTC\n'; report=inspect_csv(raw)
        self.assertEqual(len(report['accepted']),1); self.assertEqual(len(report['rejected']),1)
        self.assertIn('Spreadsheet formula',quarantine_json(report))
        with self.assertRaises(ValueError): import_catalog(self.path,'supplier-a',raw,report['source_sha256'])
        self.assertFalse(self.path.exists())
    def test_duplicate_headers_and_records(self):
        with self.assertRaises(ValueError): inspect_csv(b'sku,sku,name,price_minor,currency\n')
        self.assertEqual(len(inspect_csv(self.raw+b'SKU-1,Other,200,USD\n')['rejected']),1)
        self.assertEqual(len(inspect_csv(HEADER+b'SKU-1,Missing\n')['rejected']),1)
    def test_malformed_quoting_and_oversized_fields_raise_value_error(self):
        with self.assertRaises(ValueError): inspect_csv(HEADER+b'A,"unterminated\n')
        with self.assertRaises(ValueError): inspect_csv(HEADER+b'A,'+b'x'*200000+b',1,USD\n')
        with self.assertRaises(ValueError): import_catalog(self.path,'supplier-a',HEADER+b'A,"x','0'*64)
        self.assertFalse(self.path.exists())
    def test_changed_bytes_and_supplier_scope(self):
        with self.assertRaises(ValueError): import_catalog(self.path,'supplier-a',self.raw,'wrong')
        digest=inspect_csv(self.raw)['source_sha256']
        import_catalog(self.path,'supplier-a',self.raw,digest); import_catalog(self.path,'supplier-b',self.raw,digest)
        with sqlite3.connect(self.path) as db: self.assertEqual(db.execute('SELECT count(*) FROM catalog').fetchone()[0],2)

if __name__=='__main__': unittest.main()
