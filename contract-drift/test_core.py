# SPDX-License-Identifier: MIT
import copy
import unittest
from core import compare, validate_schema

class Tests(unittest.TestCase):
    def setUp(self): self.base={'type':'object','properties':{'id':{'type':'string'}},'required':['id'],'additionalProperties':False}
    def test_optional_addition_and_required_break(self):
        new=copy.deepcopy(self.base); new['properties']['note']={'type':'string'}
        self.assertTrue(compare(self.base,new)['compatible']); new['required'].append('note')
        self.assertFalse(compare(self.base,new)['compatible'])
    def test_removal_enum_and_type_changes(self):
        new=copy.deepcopy(self.base); new['properties']={}; new['required']=[]
        self.assertFalse(compare(self.base,new)['compatible'])
        self.assertFalse(compare({'type':'string','enum':['a','b']},{'type':'string','enum':['a']})['compatible'])
        self.assertTrue(compare({'type':'integer'},{'type':'number'})['compatible'])
        self.assertFalse(compare({'type':'number'},{'type':'integer'})['compatible'])
    def test_nested_arrays(self):
        self.assertFalse(compare({'type':'array','items':{'type':'string'}},{'type':'array','items':{'type':'integer'}})['compatible'])
    def test_unsupported_fails_closed(self):
        for schema in ({'type':'string','pattern':'x'}, {'$ref':'other.json'}, {'type':'array'}, {'type':'object','required':['missing']}):
            with self.assertRaises(ValueError): validate_schema(schema)
    def test_new_constraints_on_open_object_are_flagged(self):
        self.assertFalse(compare({'type':'object'},{'type':'object','properties':{'x':{'type':'string'}}})['compatible'])
    def test_wider_number_type_with_narrow_enum_is_breaking(self):
        self.assertFalse(compare({'type':'integer'},{'type':'number','enum':[1]})['compatible'])

if __name__=='__main__': unittest.main()
