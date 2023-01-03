# jyuusu

`jyuusu` （ジュース） is a dependency injection system implemented in Python. Its design and interface are heavily 
inspired by Google's [Guice](https://github.com/google/guice) and [Dagger 2](https://dagger.dev/).

While the library's name is `jyuusu`, the PYPI package name is `pmkg-jyuusu` to avoid collisions. However, I don't
think I will upload the package to PYPI in the near future.

## Requirement

The library should work with Python 3.8 or later.

## Installation

You can just simply copy the `src/jyuusu` directory into your code base, or you can use the following tools.

### Pip

```
pip install git+https://github.com/pkhungurn/jyuusu.git
```

### Poetry

```
poetry add git+https://github.com/pkhungurn/jyuusu.git
```

## How to Use

Take a look at the [unit tests](tests/binder_test.py) to get glimpse on how the library is supposed to be used. 

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

* [2022/01/03] First release (v0.1.0).
