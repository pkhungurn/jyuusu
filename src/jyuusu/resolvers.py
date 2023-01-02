import typing

from jyuusu.injector import Resolver, Injector
from jyuusu.binding_keys import BindingKey, SimpleTypeBindingKey, ToDictBindingKey
from jyuusu.read_writer_monitor import ReadWriteMonitor


class DictResolver(Resolver):
    def __init__(self, dict_type: type, to_dict_binding_keys: typing.Set[ToDictBindingKey]):
        self.to_dict_binding_keys = to_dict_binding_keys
        self.dict_type = dict_type

    def resolve(self, injector: Injector,
                binding_key_stack: typing.OrderedDict[BindingKey, typing.Any]) -> typing.Any:
        result = {}
        for key in self.to_dict_binding_keys:
            value = injector.get_instance_internal(key, binding_key_stack)
            result[key.key_value] = value
        return result

    def add_key(self, key: ToDictBindingKey):
        assert key not in self.to_dict_binding_keys
        self.to_dict_binding_keys.add(key)


class InstanceResolver(Resolver):
    def __init__(self, value: typing.Any):
        self.value = value

    def resolve(self, injector: Injector,
                binding_key_stack: typing.OrderedDict[BindingKey, typing.Any]) -> typing.Any:
        return self.value


class DelegatedResolver(Resolver):
    def __init__(self, binding_key: SimpleTypeBindingKey):
        self.binding_key = binding_key

    def resolve(self, injector: 'Injector',
                binding_key_stack: typing.OrderedDict[BindingKey, typing.Any]) -> typing.Any:
        return injector.get_instance_internal(self.binding_key, binding_key_stack)


class MemoizedResolver(Resolver):
    def __init__(self, base_resolver: Resolver):
        self.base_resolver = base_resolver
        self.read_write_monitor = ReadWriteMonitor()
        self.value: typing.Any = None

    def resolve(self,
                injector: Injector,
                binding_key_stack: typing.OrderedDict[BindingKey, typing.Any]) -> typing.Any:
        with self.read_write_monitor.read_session():
            value = self.value
        if value is not None:
            return value
        with self.read_write_monitor.write_session():
            if self.value is None:
                self.value = self.base_resolver.resolve(injector, binding_key_stack)
        return self.value