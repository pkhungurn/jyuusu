# jyuusu

`jyuusu` （ジュース） is a dependency injection system implemented in Python. Its design and interface is heavily inspired by Google's [Guice](https://github.com/google/guice) and [Dagger 2](https://dagger.dev/).

## Requirement

The library should work with Python 3.8 or later.

## Installation

There's no automatic installation system. Just copy the `src/jyuusu` directory into your code base.

## How to Use

Take a look at the [unit tests](src/jyuusu/binder_test.py) to get a glimpse on how the library is supposed to be used. 

Well, here's a test method.

```python
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
```

## Update History

* [2022/01/03] First release.
