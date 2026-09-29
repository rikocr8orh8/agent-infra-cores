# SPDX-License-Identifier: MIT
import tempfile
import unittest
from pathlib import Path
from core import Tape

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.path=Path(self.tmp.name)/'db'
        self.tape=Tape(self.path,['id'],['status'],['page'])
    def record(self): self.tape.record('GET','https://api.example.test/orders?page=1&token=SECRET',{'id':'1','password':'SECRET'},200,{'status':'ready','api_key':'SECRET'})
    def test_projection_and_offline_replay(self):
        self.record(); self.assertNotIn('SECRET',str(self.tape.export()))
        result=self.tape.replay('GET','https://api.example.test/orders?token=OTHER&page=1',{'id':'1','password':'OTHER'})
        self.assertEqual(result,{'status':200,'body':{'status':'ready'}})
    def test_missing_fixture_never_falls_back(self):
        self.record()
        with self.assertRaises(ValueError): self.tape.replay('GET','https://api.example.test/orders?page=2',{'id':'1'})
    def test_ambiguous_recording_rejected(self):
        self.record()
        with self.assertRaises(ValueError): self.tape.record('GET','https://api.example.test/orders?page=1',{'id':'1'},500,{'status':'failed'})
    def test_policy_changes_and_nested_fields_rejected(self):
        with self.assertRaises(ValueError): Tape(self.path,['id','password'],['status'],['page'])
        with self.assertRaises(ValueError): self.tape.record('GET','https://api.example.test/orders',{'id':{'secret':'hidden'}},200,{})
        with self.assertRaises(ValueError): self.tape.request('GET','https://user:pass@api.example.test',{})

if __name__=='__main__': unittest.main()
