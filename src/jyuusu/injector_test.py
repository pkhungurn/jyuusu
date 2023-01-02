import unittest
from typing import Dict
from unittest import TestCase

from jyuusu.injector import Injector
from jyuusu.binding_keys import SimpleTypeBindingKey, ToDictBindingKey
from jyuusu.resolvers import DictResolver, InstanceResolver, DelegatedResolver, MemoizedResolver
from jyuusu.constructor_resolver import ConstructorResolver, ResolverSpec, ProviderType
from jyuusu.provider import Provider


class InjectorTest(TestCase):
    def test_instance_resolver(self):
        injector = Injector({
            SimpleTypeBindingKey(int): InstanceResolver(10),
            SimpleTypeBindingKey(float): InstanceResolver(2.5),
            SimpleTypeBindingKey(bool, 'a'): InstanceResolver(False),
            SimpleTypeBindingKey(bool, 'b'): InstanceResolver(True)
        })

        self.assertEqual(injector.get_instance(int), 10)
        self.assertEqual(injector.get_instance(float), 2.5)
        self.assertEqual(injector.get_instance(bool, 'a'), False)
        self.assertEqual(injector.get_instance(bool, 'b'), True)

    def test_constructor_resolver(self):
        class A:
            def __init__(self, d0: int, d1: int):
                self.d1 = d1
                self.d0 = d0

        a_resolver = ConstructorResolver(A, {
            'd0': ResolverSpec(SimpleTypeBindingKey(int, 'd0')),
            'd1': ResolverSpec(SimpleTypeBindingKey(int, 'd1')),
        })
        injector = Injector({
            SimpleTypeBindingKey(int, 'd0'): InstanceResolver(10),
            SimpleTypeBindingKey(int, 'd1'): InstanceResolver(20),
            SimpleTypeBindingKey(A): a_resolver
        })

        a = injector.get_instance(A)

        self.assertEqual(a.d0, 10)
        self.assertEqual(a.d1, 20)

    def test_constructor_resolver_different_instance(self):
        class A:
            def __init__(self, d0: int, d1: int):
                self.d1 = d1
                self.d0 = d0

        a_resolver = ConstructorResolver(A, {
            'd0': ResolverSpec(SimpleTypeBindingKey(int, 'd0')),
            'd1': ResolverSpec(SimpleTypeBindingKey(int, 'd1')),
        })
        injector = Injector({
            SimpleTypeBindingKey(int, 'd0'): InstanceResolver(10),
            SimpleTypeBindingKey(int, 'd1'): InstanceResolver(20),
            SimpleTypeBindingKey(A): a_resolver
        })

        a0 = injector.get_instance(A)
        a1 = injector.get_instance(A)

        self.assertNotEqual(a0, a1)

    def test_constructor_resolver_memoized(self):
        class A:
            def __init__(self, d0: int, d1: int):
                self.d1 = d1
                self.d0 = d0

        a_resolver = ConstructorResolver(A, {
            'd0': ResolverSpec(SimpleTypeBindingKey(int, 'd0')),
            'd1': ResolverSpec(SimpleTypeBindingKey(int, 'd1')),
        })
        injector = Injector({
            SimpleTypeBindingKey(int, 'd0'): InstanceResolver(10),
            SimpleTypeBindingKey(int, 'd1'): InstanceResolver(20),
            SimpleTypeBindingKey(A): MemoizedResolver(a_resolver)
        })

        a0 = injector.get_instance(A)
        a1 = injector.get_instance(A)

        self.assertEqual(a0, a1)

    def test_dict_resolver(self):
        injector = Injector({
            SimpleTypeBindingKey(Dict[str, int]): DictResolver(
                Dict[str, int],
                {
                    ToDictBindingKey(Dict[str, int], "a"),
                    ToDictBindingKey(Dict[str, int], "b"),
                    ToDictBindingKey(Dict[str, int], "c")
                }),
            ToDictBindingKey(Dict[str, int], "a"): InstanceResolver(10),
            ToDictBindingKey(Dict[str, int], "b"): InstanceResolver(20),
            ToDictBindingKey(Dict[str, int], "c"): InstanceResolver(30),
        })

        v = injector.get_instance(Dict[str, int])

        self.assertEqual(v["a"], 10)
        self.assertEqual(v["b"], 20)
        self.assertEqual(v["c"], 30)

    def test_delegated_resolver(self):
        class A:
            def __init__(self):
                self.value = 10

        injector = Injector({
            SimpleTypeBindingKey(A): ConstructorResolver(A, {}),
            SimpleTypeBindingKey(A, "a"): DelegatedResolver(SimpleTypeBindingKey(A))
        })

        v = injector.get_instance(A, "a")

        self.assertEqual(v.value, 10)

    def test_circular_dependency(self):
        class A:
            def __init__(self, b: 'B'):
                self.b = b

        class B:
            def __init__(self, a: A):
                self.a = A

        injector = Injector({
            SimpleTypeBindingKey(A): ConstructorResolver(A, {'b': ResolverSpec(SimpleTypeBindingKey(B))}),
            SimpleTypeBindingKey(B): ConstructorResolver(B, {'a': ResolverSpec(SimpleTypeBindingKey(A))})
        })

        self.assertRaises(RuntimeError, lambda: injector.get_instance(A))

    def test_provider_injection(self):
        class A:
            def __init__(self, b_provider: Provider['B']):
                self.value = 10
                self.b_provider = b_provider

            def get_b(self):
                return self.b_provider.get()

        class B:
            def __init__(self, a: A):
                self.value = 20
                self.a = a

        injector = Injector({
            SimpleTypeBindingKey(A): ConstructorResolver(
                A,
                {'b_provider': ResolverSpec(SimpleTypeBindingKey(B), ProviderType.PROVIDER)}),
            SimpleTypeBindingKey(B): ConstructorResolver(
                B,
                {'a': ResolverSpec(SimpleTypeBindingKey(A))})
        })

        a = injector.get_instance(A)

        self.assertEqual(a.value, 10)
        self.assertEqual(a.get_b().value, 20)
        self.assertEqual(a.get_b().a.value, 10)


if __name__ == "__main__":
    unittest.main()
