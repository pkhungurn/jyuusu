import inspect
import typing
from dataclasses import dataclass
from enum import Enum
from inspect import FullArgSpec
from typing import Dict

from jyuusu.injector import Resolver, Injector, ProviderUsingInjector
from jyuusu.binding_keys import BindingKey, SimpleTypeBindingKey
from jyuusu.provider import Provider, Lazy
from jyuusu.resolvers import MemoizedResolver


def normalize_dict_type(type_: type) -> type:
    if typing.get_origin(type_) == dict:
        return Dict[typing.get_args(type_)]
    else:
        return type_


class ProviderType(Enum):
    VALUE = 1
    PROVIDER = 2
    LAZY = 3


@dataclass
class ResolverSpec:
    binding_key: SimpleTypeBindingKey
    provider_type: ProviderType = ProviderType.VALUE

    @staticmethod
    def of(type_: type, tag: typing.Optional[str] = None):
        return ResolverSpec(SimpleTypeBindingKey(type_, tag))

    @staticmethod
    def provider(type_: type, tag: typing.Optional[str] = None):
        return ResolverSpec(SimpleTypeBindingKey(type_, tag), ProviderType.PROVIDER)

    @staticmethod
    def lazy(type_: type, tag: typing.Optional[str] = None):
        return ResolverSpec(SimpleTypeBindingKey(type_, tag), ProviderType.LAZY)


class ConstructorResolver(Resolver):
    def __init__(self, constructor: typing.Callable, arg_resolver_specs: typing.Dict[str, ResolverSpec]):
        self.constructor = constructor
        self.arg_resolver_specs = arg_resolver_specs

    def resolve(self,
                injector: Injector,
                binding_key_stack: typing.OrderedDict[BindingKey, typing.Any]) -> typing.Any:
        kwargs = {}
        for (key, resolver_spec) in self.arg_resolver_specs.items():
            if resolver_spec.provider_type == ProviderType.VALUE:
                value = injector.get_instance_internal(resolver_spec.binding_key, binding_key_stack)
            elif resolver_spec.provider_type == ProviderType.PROVIDER:
                value = ProviderUsingInjector(injector, resolver_spec.binding_key)
            else:
                value = Lazy(ProviderUsingInjector(injector, resolver_spec.binding_key))
            kwargs[key] = value
        instance = self.constructor(**kwargs)
        return instance


def assert_valid_constructor_and_resolver_specs(constructor_arg_spec: FullArgSpec,
                                                resolver_specs: Dict[str, typing.Union[str, ResolverSpec]],
                                                is_class_constructor: bool = False):
    if is_class_constructor:
        assert len(constructor_arg_spec.args) > 0, "The constructor has 0 arguments!"
        assert constructor_arg_spec.args[0] not in resolver_specs, \
            f"The first argument of the constructor ({constructor_arg_spec.args[0]}) is in resolver_specs!"

    assert constructor_arg_spec.defaults is None, f"The constructor has default parameters!"
    assert constructor_arg_spec.varargs is None, f"The constructor has varargs!"
    assert constructor_arg_spec.varkw is None, f"The constructor has varkw"
    assert len(constructor_arg_spec.kwonlyargs) == 0, f"The constructor has kwonlyargs"
    assert constructor_arg_spec.kwonlydefaults is None, f"The constructor has kwonlydefaults!"


def resolve_forward_refs(type_: type):
    if isinstance(type_, typing.ForwardRef):
        print("INFO: ForwardRef", type_)
        print("INFO:", type_.__forward_arg__)
        forwarded_type = eval(type_.__forward_arg__)
        print(forwarded_type)
    elif isinstance(type_, str):
        print("INFO: String", type_)
    return type_


def get_resolver_spec(
        arg_name: str,
        constructor_arg_spec: FullArgSpec,
        user_specified_resolver_specs: Dict[str, typing.Union[str, ResolverSpec]]):
    if arg_name in constructor_arg_spec.annotations:
        bypass_constructor_annotation = False
        tag = None
        spec = None
        if arg_name in user_specified_resolver_specs:
            spec = user_specified_resolver_specs[arg_name]
            if isinstance(spec, ResolverSpec):
                bypass_constructor_annotation = True
            elif isinstance(spec, str):
                tag = spec
            else:
                raise AssertionError(f"The resolved spec under the key {arg_name} is not a string or a ResolverSpec.")
        if not bypass_constructor_annotation:
            arg_type = constructor_arg_spec.annotations[arg_name]
            arg_type = resolve_forward_refs(arg_type)
            origin = typing.get_origin(arg_type)
            if origin == Provider:
                assert len(typing.get_args(arg_type)) == 1
                underlying_type = normalize_dict_type(typing.get_args(arg_type)[0])
                spec = ResolverSpec.provider(underlying_type, tag)
            elif origin == Lazy:
                assert len(typing.get_args(arg_type)) == 1
                underlying_type = normalize_dict_type(typing.get_args(arg_type)[0])
                spec = ResolverSpec.lazy(underlying_type, tag)
            else:
                spec = ResolverSpec.of(normalize_dict_type(arg_type), tag)
    else:
        assert arg_name in user_specified_resolver_specs, \
            f"The argument '{arg_name}' of the constructor has not annotation, " \
            f"but it does not appear as a key in resolver_specs."
        spec = user_specified_resolver_specs[arg_name]
        assert isinstance(spec, ResolverSpec), \
            f"The argument '{arg_name}' of the constructor has no annotation, " \
            f"but its resolver_specs entry is not an instance of SimpleTypeBindingKey."
    assert spec is not None
    return spec


def get_constructor_arg_resolver_specs(
        constructor_arg_spec: FullArgSpec,
        users_specified_resolved_specs: Dict[str, typing.Union[str, ResolverSpec]],
        is_class_constructor: bool = False) -> typing.Dict[str, ResolverSpec]:
    assert_valid_constructor_and_resolver_specs(constructor_arg_spec, users_specified_resolved_specs,
                                                is_class_constructor)

    for arg_name in users_specified_resolved_specs:
        assert arg_name in constructor_arg_spec.args, \
            f"A key ({arg_name}) in resolver_specs is not in the constructor's argument list!"

    args_resolver_specs = {}
    if is_class_constructor:
        start = 1
    else:
        start = 0
    for i in range(start, len(constructor_arg_spec.args)):
        arg_name = constructor_arg_spec.args[i]
        spec = get_resolver_spec(arg_name, constructor_arg_spec, users_specified_resolved_specs)
        args_resolver_specs[arg_name] = spec
    return args_resolver_specs


def create_resolver(constructor: typing.Callable, **kwargs):
    arg_resolver_specs = get_constructor_arg_resolver_specs(
        inspect.getfullargspec(constructor), kwargs, is_class_constructor=False)
    return ConstructorResolver(constructor, arg_resolver_specs)


def create_jyuusu_class_installation_module(klass: type):
    from jyuusu.binder import Module, Binder
    class _JyuusuModule(Module):
        def configure(self, binder: Binder):
            binder.add_binding(SimpleTypeBindingKey(klass), klass._create_jyuusu_resolver())

    return _JyuusuModule


def add_resolver_factory_and_module(klass: type, resolver_specs: Dict[str, typing.Union[str, ResolverSpec]]) -> type:
    assert inspect.isclass(klass), "The input 'klass' is not a class!"
    if '__init__' not in klass.__dict__:
        def __init__(self):
            pass

        full_arg_spec = inspect.getfullargspec(__init__)
    else:
        assert inspect.isfunction(klass.__init__), f"{klass}'s __init__ is not a function"
        full_arg_spec = inspect.getfullargspec(klass.__init__)

    args_resolver_specs = get_constructor_arg_resolver_specs(full_arg_spec, resolver_specs, is_class_constructor=True)

    def _create_jyuusu_resolver() -> Resolver:
        return ConstructorResolver(klass, args_resolver_specs)

    klass._create_jyuusu_resolver = staticmethod(_create_jyuusu_resolver)
    klass._JyuusuModule = create_jyuusu_class_installation_module(klass)
    return klass


def injectable_class_with_specs(**kwargs):
    def _add_resolver(klass):
        return add_resolver_factory_and_module(klass, kwargs)

    return _add_resolver


def make_injectable_class(klass: type, **kwargs):
    add_resolver = injectable_class_with_specs(**kwargs)
    return add_resolver(klass)


def injectable_class(klass: type) -> type:
    return add_resolver_factory_and_module(klass, {})


def is_class_injectable(klass: type) -> bool:
    from jyuusu.binder import Module
    if not inspect.isclass(klass):
        return False
    elif not "_create_jyuusu_resolver" in klass.__dict__:
        return False
    elif not inspect.isfunction(klass._create_jyuusu_resolver):
        return False
    elif not "_JyuusuModule" in klass.__dict__:
        return False
    elif not inspect.isclass(klass._JyuusuModule):
        return False
    elif not issubclass(klass._JyuusuModule, Module):
        return False

    resolver_signature = inspect.signature(klass._create_jyuusu_resolver)
    if resolver_signature.return_annotation != Resolver:
        return False
    elif len(resolver_signature.parameters) != 0:
        return False

    if "__init__" not in klass._JyuusuModule.__dict__:
        return True
    jyuusu_module_init_signature = inspect.signature(klass._JyuusuModule.__init__)
    return len(jyuusu_module_init_signature.parameters) == 0


def class_module(klass: type):
    assert is_class_injectable(klass)
    return klass._JyuusuModule


def memoized(klass):
    assert is_class_injectable(klass), "Input is not injectable!"
    old_factory = klass._create_jyuusu_resolver

    def _create_jyuusu_resolver() -> Resolver:
        return MemoizedResolver(old_factory())

    klass._create_jyuusu_resolver = staticmethod(_create_jyuusu_resolver)
    return klass
