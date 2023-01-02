import typing
from abc import ABC, abstractmethod
from typing import Dict, Set, Optional

from jyuusu.binding_keys import BindingKey, SimpleTypeBindingKey, ToDictBindingKey
from jyuusu.constructor_resolver import create_resolver, class_module
from jyuusu.injector import Resolver
from jyuusu.resolvers import InstanceResolver, DelegatedResolver, MemoizedResolver, DictResolver


class AbstractBindingSubject(ABC):
    def __init__(self, binder: 'Binder', type_: type, tag: Optional[str] = None):
        self.tag = tag
        self.type_ = type_
        self.binder = binder
        self.memoized = False

    @abstractmethod
    def get_binding_key(self) -> BindingKey:
        pass

    @abstractmethod
    def add_binding(self, resolver: Resolver):
        pass

    def with_tag(self, tag: str):
        assert self.tag is None
        self.tag = tag
        return self

    def with_memoization(self):
        assert self.memoized == False
        self.memoized = True
        return self

    def to_instance(self, value: typing.Any):
        assert not self.memoized
        self.add_binding(InstanceResolver(value))
        return self

    def wrap_if_memoized(self, resolver: Resolver):
        if self.memoized:
            return MemoizedResolver(resolver)
        else:
            return resolver

    def to_type(self, type_: type):
        self.add_binding(self.wrap_if_memoized(DelegatedResolver(SimpleTypeBindingKey(type_))))
        return self.binder

    def to_tagged_type(self, type_: type, tag: str):
        self.add_binding(self.wrap_if_memoized(DelegatedResolver(SimpleTypeBindingKey(type_, tag))))
        return self.binder

    def to_resolver(self, resolver: Resolver):
        self.add_binding(self.wrap_if_memoized(resolver))
        return self.binder

    def to_constructor(self, constructor: typing.Callable, **kwargs):
        resolver = create_resolver(constructor, **kwargs)
        self.to_resolver(resolver)
        return self.binder


class SimpleTypeBindingSubject(AbstractBindingSubject):
    def __init__(self, binder: 'Binder', type_: type, tag: Optional[str] = None):
        super().__init__(binder, type_, tag)
        assert typing.get_origin(type_) != dict

    def get_binding_key(self):
        return SimpleTypeBindingKey(self.type_, self.tag)

    def add_binding(self, resolver: Resolver):
        self.binder.add_binding(self.get_binding_key(), resolver)


def normalize_dict_type(type_: type):
    assert typing.get_origin(type_) == dict
    return typing.Dict[typing.get_args(type_)]


class DictBindingSubject(AbstractBindingSubject):
    def __init__(self, binder: 'Binder', dict_type: type, tag: Optional[str] = None):
        dict_type = normalize_dict_type(dict_type)
        super().__init__(binder, dict_type, tag)
        self.simple_key = SimpleTypeBindingKey(dict_type, tag)
        self.dict_key: Optional[typing.Union[str, int, type]] = None

    def with_key(self, key: typing.Union[str, int, type]):
        self.key = key
        return self

    def get_binding_key(self) -> ToDictBindingKey:
        assert self.key is not None
        return ToDictBindingKey(self.type_, self.key, self.tag)

    def add_binding(self, resolver: Resolver):
        assert self.simple_key in self.binder.bindings
        dict_resolver = self.binder.bindings[self.simple_key]
        assert isinstance(dict_resolver, DictResolver)
        dict_resolver.add_key(self.get_binding_key())
        self.binder.add_binding(self.get_binding_key(), resolver)


class Binder:
    def __init__(self):
        self.bindings: Dict[BindingKey, Resolver] = {}
        self.installed_modules: Set[type] = set()

    def add_binding(self, key: BindingKey, resolver: Resolver):
        assert key not in self.bindings
        self.bindings[key] = resolver
        return self

    def install_class(self, klass: type):
        return self.install_module(class_module(klass))

    def install_dict(self, key_type: type, value_type: type, tag: Optional[str] = None):
        assert key_type in [str, int, type]
        dict_type = typing.Dict[key_type, value_type]
        simple_key = SimpleTypeBindingKey(dict_type, tag)
        if simple_key in self.bindings:
            return
        self.add_binding(simple_key, DictResolver(dict_type, set()))
        return self

    def bind(self, type_: type, tag: Optional[str] = None):
        return SimpleTypeBindingSubject(self, type_, tag)

    def bind_to_dict(self, key_type: type, value_type: type, tag: Optional[str] = None):
        assert key_type in [str, int, type]
        return DictBindingSubject(self, Dict[key_type, value_type], tag)

    def install_module(self, module: type):
        if module in self.installed_modules:
            return
        self.installed_modules.add(module)
        module().configure(self)
        return self


class Module(ABC):
    @abstractmethod
    def configure(self, binder: Binder):
        pass
