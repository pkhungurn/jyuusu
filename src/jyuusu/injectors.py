from jyuusu.binder import Binder
from jyuusu.injector import Injector


def create_injector(*args):
    binder = Binder()
    for module in args:
        binder.install_module(module)
    return Injector(binder.bindings)
