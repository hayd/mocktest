from mocktest import pending ##TODO: FIX

import os
import sys
this_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if not this_dir in sys.path:
	sys.path.insert(0, this_dir)

from mocktest import TestCase

from mocktest import mock_on, raw_mock, mock_wrapper
import mocktest

class MockObjectAndWrapperTest(TestCase):
	def test_constructor(self):
		mock = raw_mock()
		wrapper = mock_wrapper(mock)
		self.assertFalse(wrapper.called, "called not initialised correctly")
		self.assertTrue(wrapper.called.exactly(0), "call_count not initialised correctly")

		self.assertEquals(wrapper.call_list, [])
		self.assertEquals(wrapper._children, {})
		self.assertEquals(wrapper.action, None)
		self.assertEquals(wrapper.name, 'unnamed mock')
		wrapper.name = 'lil bobby mock'
	
	def test_default_return_value(self):
		wrapper = mock_wrapper()
		mock = wrapper.mock
		self.assertTrue(wrapper.return_value is mocktest.mock.DEFAULT)
		retval = mock()
		self.assertEqual(retval.__class__, raw_mock().__class__)
		self.assertEqual(mock_wrapper(retval).name, 'return value for (unnamed mock)')
		self.assertEquals(wrapper.return_value.__class__, raw_mock().__class__)
	
	def test_default_accessor_value(self):
		wrapper = mock_wrapper()
		mock = wrapper.mock
		retval = mock.child_a
		self.assertEqual(retval.__class__, raw_mock().__class__)
		self.assertEqual(mock_wrapper(retval).name, 'child_a')
		
	def test_return_value(self):
		wrapper = mock_wrapper().returning(None)
		self.assertEquals(None, wrapper.return_value)
		self.assertEquals(None, wrapper.mock())
	
	def assert_mock_is_frozen(self, wrapper):
		self.assertFalse(wrapper._modifiable_children)
		self.assertRaises(AttributeError, lambda: wrapper.mock.nonexistant_child)
		def set_thingie():
			wrapper.mock.set_nonexistant_child = 'x'
		self.assertRaises(AttributeError, lambda: set_thingie())
		
	def test_with_methods_should_set_return_values_and_freeze_mock(self):
		wrapper = mock_wrapper().with_methods('blob', foo='bar', x=123)
		mock = wrapper.mock
		
		self.assertEqual(mock.blob().__class__, raw_mock().__class__)
		self.assertEqual(mock.foo(), 'bar')
		self.assertEqual(mock.x(), 123)
		
		self.assertEqual(sorted(wrapper._children.keys()), ['blob', 'foo','x'])
		self.assert_mock_is_frozen(wrapper)

	def test_with_children_should_set_return_values_and_freeze_mock(self):
		wrapper = mock_wrapper().with_children('blob', foo='bar', x=123)
		mock = wrapper.mock
		
		self.assertEqual(mock.blob.__class__, raw_mock().__class__)
		self.assertEqual(mock.foo, 'bar')
		self.assertEqual(mock.x, 123)
		
		self.assertEqual(sorted(wrapper._children.keys()), ['blob', 'foo','x'])
		self.assert_mock_is_frozen(wrapper)
	
	def test_name_as_first_arg_in_constructor(self):
		wrapper = mock_wrapper(raw_mock("li'l mocky"))
		self.assertEqual(wrapper.name, "li'l mocky")

	class SpecClass:
		b = "bee"
		__something__ = None
		def a(self):
			return "foo"
		
		
	def test_spec_class_in_constructor(self):
		wrapper = mock_wrapper().with_spec(self.SpecClass)
		self.assertEqual(wrapper._children.keys(), ['a','b'])
		self.assertTrue(isinstance(wrapper.mock.a(), raw_mock().__class__))
		self.assert_mock_is_frozen(wrapper)
		
		self.assertRaises(AttributeError, lambda: wrapper.mock.__something__)

	def test_spec_instance_in_constructor(self):
		wrapper = mock_wrapper().with_spec(self.SpecClass())
		self.assertEqual(wrapper._children.keys(), ['a','b'])
		self.assertTrue(isinstance(wrapper.mock.a(), raw_mock().__class__))
		self.assert_mock_is_frozen(wrapper)
		self.assertRaises(AttributeError, lambda: wrapper.mock.__something__)
	
	def test_children_can_be_added_later(self):
		wrapper = mock_wrapper()
		wrapper.mock.foo = 1
		wrapper.mock.bar = 2
		self.assertEqual(wrapper._children, {'foo':1, 'bar':2})
	
	def test_frozen(self):
		wrapper = mock_wrapper().frozen().unfrozen()
		wrapper.mock.child_a = 'baz'
		self.assertEqual(wrapper.mock.child_a, 'baz')
		
		wrapper = mock_wrapper().frozen()
		self.assert_mock_is_frozen(wrapper)
	
	def test_children_and_methods_can_coexist(self):
		wrapper = mock_wrapper().with_children(a='a').unfrozen().with_methods(b='b')
		self.assertEqual(wrapper.mock.a, 'a')
		self.assertEqual(wrapper.mock.b(), 'b')
	
	def test_side_effect_is_called(self):
		wrapper = mock_wrapper()
		def effect():
			raise SystemError('kablooie')
		wrapper.action = effect
		
		self.assertRaises(SystemError, wrapper.mock)
		self.assertEquals(True, wrapper.called)
		
		results = []
		def effect(n):
			results.append('call %s' % (n,))
		wrapper.action = effect
		
		wrapper.mock(1)
		self.assertEquals(results, ['call 1'])
		wrapper.mock(2)
		self.assertEquals(results, ['call 1','call 2'])
	
		sentinel = object()
		wrapper = mock_wrapper().with_action(sentinel)
		self.assertEquals(wrapper.action, sentinel)
	
	def test_side_effect_return_used_when_return_value_not_specified(self):
		def return_foo():
			return "foo"
		wrapper = mock_wrapper().with_action(return_foo)
		self.assertEqual(wrapper.mock(), 'foo')
	
	def test_side_effect_can_change_mock_return_value(self):
		wrapper = mock_wrapper()
		def modify_it():
			wrapper.return_value = 'foo'
		wrapper.action = modify_it
		self.assertEqual(wrapper.mock(), 'foo')
	
	def test_side_effect_can_remove_mock_return_value_and_replace_it(self):
		wrapper = mock_wrapper()
		wrapper.return_value = "not me"
		def modify_it():
			del wrapper.return_value
			return "me instead"
		wrapper.action = modify_it
		self.assertEqual(wrapper.mock(), "me instead")
	
	def test_side_effect_return_val_used_even_when_it_is_none(self):
		def return_foo():
			print "i've been called!"
		wrapper = mock_wrapper().with_action(return_foo)
		self.assertEqual(wrapper.mock(), None)
	
	def test_side_effect_return_not_used_when_return_value_specified(self):
		def return_foo():
			return "foo"
		wrapper = mock_wrapper().returning('bar').with_action(return_foo)
		self.assertEqual(wrapper.mock(), 'bar')
	
	def test_call_recording(self):
		wrapper = mock_wrapper()
		mock = wrapper.mock
		
		result = mock()
		self.assertEquals(mock(), result, "different result from consecutive calls")
		self.assertEquals(wrapper.call_list,
			[
				((),{}), # called with nothing
				((),{}), # (twice)
			])

		wrapper.reset()
		self.assertEquals(wrapper.call_list, [])
		
		mock('first_call')
		mock('second_call', 'arg2', call_=2)
		self.assertEquals(wrapper.call_list,
			[
				(('first_call',),{}),
				(('second_call','arg2'), {'call_':2}),
			])

