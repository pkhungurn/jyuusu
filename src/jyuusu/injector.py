import typing
from abc import ABC, abstractmethod
from collections import OrderedDict
from threading import Lock

from jyuusu.binding_keys import BindingKey, SimpleTypeBindingKey
from jyuusu.provider import Provider


class Resolver(ABC):
    @abstractmethod
    def resolve(self,
                injector: 'Injector',
                binding_key_stack: typing.OrderedDict[BindingKey, typing.Any]) -> typing.Any:
        pass


class Injector:
    def __init__(self, bindings: typing.Dict[BindingKey, Resolver]):
        self.bindings = bindings
        self.lock = Lock()

    def get_instance(self, type_: type, tag: typing.Optional[str] = None) -> typing.Any:
        key = SimpleTypeBindingKey(type_, tag)
        return self.get_instance_internal(key, OrderedDict())

    def get_provider(self, type_: type, tag: typing.Optional[str] = None) -> Provider:
        return ProviderUsingInjector(self, SimpleTypeBindingKey(type_, tag))

    def get_resolver(self, key: BindingKey):
        from jyuusu.constructor_resolver import is_class_injectable

        with self.lock:
            if not key in self.bindings:
                if isinstance(key, SimpleTypeBindingKey) and key.tag is None and is_class_injectable(key.type_):
                    self.bindings[key] = key.type_._create_jyuusu_resolver()
                else:
                    raise AssertionError(f"Resolver for key {key} is not found.")
            resolver = self.bindings[key]
            return resolver

    def get_instance_internal(self,
                              key: BindingKey,
                              binding_key_stack: OrderedDict) -> typing.Any:
        if key in binding_key_stack:
            stack_trace = []
            for key_ in binding_key_stack:
                stack_trace.append("  " + str(key_))
            stack_trace.append("  " + str(key))
            stack_trace_string = "\n".join(stack_trace)
            raise RuntimeError(f"Circular dependency discovered!!!\n{stack_trace_string}")

        binding_key_stack[key] = None
        resolver = self.get_resolver(key)
        output = resolver.resolve(self, binding_key_stack)
        del binding_key_stack[key]
        return output


class ProviderUsingInjector(Provider):
    def __init__(self, injector: Injector, binding_key: SimpleTypeBindingKey):
        self.binding_key = binding_key
        self.injector = injector

    def get(self):
        return self.injector.get_instance(self.binding_key.type_, self.binding_key.tag)
