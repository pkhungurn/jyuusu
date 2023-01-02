import inspect
from inspect import FullArgSpec
from typing import Dict, Union, Optional

from jyuusu.constructor_resolver import ResolverSpec, assert_valid_constructor_and_resolver_specs, get_resolver_spec, \
    ProviderType, ConstructorResolver, create_jyuusu_class_installation_module
from jyuusu.injector import Resolver
from jyuusu.provider import Provider, Lazy


def get_factory_arg_resolver_specs(constructor_arg_spec: FullArgSpec,
                                   resolved_start: Optional[str],
                                   resolver_specs: Dict[str, Union[str, ResolverSpec]]) -> Dict[str, ResolverSpec]:
    assert_valid_constructor_and_resolver_specs(constructor_arg_spec, resolver_specs, is_class_constructor=True)

    if resolved_start is None:
        start_position = len(constructor_arg_spec.args)
    else:
        assert resolved_start in constructor_arg_spec.args
        start_position = constructor_arg_spec.args.index(resolved_start)
    assert start_position > 0

    args_to_be_resolved = constructor_arg_spec.args[start_position:]
    for key in resolver_specs:
        assert key in args_to_be_resolved

    args_resolver_specs = {}
    for arg_name in args_to_be_resolved:
        spec = get_resolver_spec(arg_name, constructor_arg_spec, resolver_specs)
        args_resolver_specs[arg_name] = spec
    return args_resolver_specs


def add_injectable_factory(
        klass: type,
        resolved_start: str,
        resolver_specs: Dict[str, Union[str, ResolverSpec]]):
    assert inspect.isclass(klass), "The input 'klass' is not a class!"
    if '__init__' not in klass.__dict__:
        def __init__(self):
            pass

        full_arg_spec = inspect.getfullargspec(__init__)
    else:
        assert inspect.isfunction(klass.__init__)
        full_arg_spec = inspect.getfullargspec(klass.__init__)

    args_resolver_specs = get_factory_arg_resolver_specs(full_arg_spec, resolved_start, resolver_specs)

    class _JyuusuFactory:
        def __init__(self, **kwargs):
            self.providers: Dict[str, Provider] = {}
            for arg_name in args_resolver_specs:
                self.providers[arg_name] = kwargs[arg_name]

        def create(self, *args, **kwargs):
            new_kwargs = kwargs.copy()
            for (arg_name, resolver_spec) in args_resolver_specs.items():
                if resolver_spec.provider_type == ProviderType.VALUE:
                    value = self.providers[arg_name].get()
                elif resolver_spec.provider_type == ProviderType.PROVIDER:
                    value = self.providers[arg_name]
                else:
                    value = Lazy(self.providers[arg_name])
                new_kwargs[arg_name] = value
            return klass(*args, **new_kwargs)

    factory_resolver_specs = {}
    for (arg_name, resolver_spec) in args_resolver_specs.items():
        spec = ResolverSpec(resolver_spec.binding_key, ProviderType.PROVIDER)
        factory_resolver_specs[arg_name] = spec

    def _create_jyuusu_resolver() -> Resolver:
        return ConstructorResolver(_JyuusuFactory, factory_resolver_specs)

    _JyuusuFactory._create_jyuusu_resolver = staticmethod(_create_jyuusu_resolver)
    _JyuusuFactory._JyuusuModule = create_jyuusu_class_installation_module(_JyuusuFactory)
    klass._JyuusuFactory = _JyuusuFactory
    return klass


def injectable_factory(resolved_start: str, **kwargs):
    def _add_injectable_factory(klass):
        return add_injectable_factory(klass, resolved_start, kwargs)

    return _add_injectable_factory


def make_injectable_factory(cls: type, resolved_start: str, **kwargs):
    add_injectable_factory = injectable_factory(resolved_start, **kwargs)
    return add_injectable_factory(cls)


def has_injectable_factory(cls: type):
    assert inspect.isclass(cls)
    return "_JyuusuFactory" in cls.__dict__


def factory_class(cls: type):
    assert inspect.isclass(cls)
    assert "_JyuusuFactory" in cls.__dict__
    return cls._JyuusuFactory
