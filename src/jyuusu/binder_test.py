import unittest
from typing import Dict, ForwardRef
from unittest import TestCase

from jyuusu.binder import Module, Binder
from jyuusu.constructor_resolver import injectable_class, memoized, ResolverSpec, \
    make_injectable_class
from jyuusu.factory_resolver import injectable_factory, factory_class
from jyuusu.injectors import create_injector
from jyuusu.provider import Provider, Lazy


class BinderTest(TestCase):
    def test_01(self):
        @injectable_class
        class A:
            def __init__(self):
                self.value = 10

        @injectable_class
        class B:
            def __init__(self, a: A):
                self.a = a
                self.value = 20

        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_class(A).install_class(B)

        injector = create_injector(Module_)

        a = injector.get_instance(A)
        b = injector.get_instance(B)

        self.assertEqual(a.value, 10)
        self.assertEqual(b.a.value, 10)
        self.assertNotEqual(a, b.a)

    def test_02(self):
        @memoized
        @injectable_class
        class A:
            def __init__(self):
                self.value = 10

        @injectable_class
        class B:
            def __init__(self, a: A):
                self.a = a
                self.value = 20

        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_class(A).install_class(B)

        injector = create_injector(Module_)

        a = injector.get_instance(A)
        b = injector.get_instance(B)

        self.assertEqual(a.value, 10)
        self.assertEqual(b.a.value, 10)
        self.assertEqual(a, b.a)

    def test_03(self):
        class A:
            def __init__(self):
                self.value = 10

        @injectable_class
        class B(A):
            def __init__(self):
                super().__init__()
                self.value = 20

        @injectable_class
        class C(A):
            def __init__(self):
                super().__init__()
                self.value = 30

        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_class(B)
                binder.install_class(C)
                binder.install_class(C)
                binder.install_class(B)
                binder.bind(A).to_type(B)

        injector = create_injector(Module_)

        a = injector.get_instance(A)

        self.assertEqual(a.value, 20)

    def test_04(self):
        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_dict(str, int)
                binder.bind_to_dict(str, int).with_key("a").to_instance(1)
                binder.bind_to_dict(str, int).with_key("b").to_instance(2)
                binder.bind_to_dict(str, int).with_key("c").to_instance(3)

        injector = create_injector(Module_)

        a = injector.get_instance(Dict[str, int])

        self.assertEqual(a, {"a": 1, "b": 2, "c": 3})

    def test_05(self):
        @injectable_class
        class A:
            def __init__(self, int_str_map: Dict[str, int]):
                self.int_str_map = int_str_map

        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_class(A)
                binder.install_dict(str, int)
                binder.bind_to_dict(str, int).with_key("a").to_instance(1)
                binder.bind_to_dict(str, int).with_key("b").to_instance(2)
                binder.bind_to_dict(str, int).with_key("c").to_instance(3)

        injector = create_injector(Module_)

        a = injector.get_instance(A)

        self.assertEqual(a.int_str_map, {"a": 1, "b": 2, "c": 3})

    def test_06(self):
        @injectable_class
        class A:
            def __init__(self, int_str_map: Provider[Dict[str, int]]):
                self.int_str_map = int_str_map

        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_class(A)
                binder.install_dict(str, int)
                binder.bind_to_dict(str, int).with_key("a").to_instance(1)
                binder.bind_to_dict(str, int).with_key("b").to_instance(2)
                binder.bind_to_dict(str, int).with_key("c").to_instance(3)

        injector = create_injector(Module_)

        a = injector.get_instance(A)

        self.assertEqual(a.int_str_map.get(), {"a": 1, "b": 2, "c": 3})

    def test_07(self):
        @injectable_class
        class A:
            def __init__(self, int_str_map: Lazy[Dict[str, int]]):
                self.int_str_map = int_str_map

        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_class(A)
                binder.install_dict(str, int)
                binder.bind_to_dict(str, int).with_key("a").to_instance(1)
                binder.bind_to_dict(str, int).with_key("b").to_instance(2)
                binder.bind_to_dict(str, int).with_key("c").to_instance(3)

        injector = create_injector(Module_)

        a = injector.get_instance(A)

        self.assertEqual(a.int_str_map.get(), {"a": 1, "b": 2, "c": 3})

    def test_08(self):
        @injectable_class
        class A:
            def __init__(self):
                self.value = 10

        @injectable_class
        class B:
            def __init__(self):
                self.value = 20

        @injectable_class
        class C:
            def __init__(self):
                self.value = 30

        @injectable_factory(resolved_start='a')
        class D:
            def __init__(self, value: int, a: A, b: B, c: C):
                self.c = c
                self.b = b
                self.a = a
                self.value = value

        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_class(A)
                binder.install_class(B)
                binder.install_class(C)
                binder.install_class(factory_class(D))

        injector = create_injector(Module_)

        d_factory = injector.get_instance(factory_class(D))
        d = d_factory.create(50)

        self.assertEqual(d.value, 50)
        self.assertEqual(d.a.value, 10)
        self.assertEqual(d.b.value, 20)
        self.assertEqual(d.c.value, 30)

    def test_09(self):
        class A:
            def __init__(self, b: ForwardRef("B")):
                self.b = b
                self.value = 10

        @injectable_class
        class B:
            def __init__(self):
                self.value = 20

        make_injectable_class(A, b=ResolverSpec.of(B))

        class Module_(Module):
            def configure(self, binder: Binder):
                binder.install_class(A)
                binder.install_class(B)

        injector = create_injector(Module_)

        a = injector.get_instance(A)

        self.assertEqual(a.value, 10)
        self.assertEqual(a.b.value, 20)

    def test10(self):
        @injectable_class
        class A:
            def __init__(self):
                self.value = 10

        @injectable_class
        class B:
            def __init__(self, a: A):
                self.a = a
                self.value = 20

        injector = create_injector()

        b = injector.get_instance(B)

        self.assertEqual(b.value, 20)
        self.assertEqual(b.a.value, 10)


if __name__ == "__main__":
    unittest.main()
