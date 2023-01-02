import typing
from abc import ABC
from dataclasses import dataclass

from jyuusu.type_util import check_is_type_all_the_way_down


class BindingKey(ABC):
    pass


@dataclass(eq=True, frozen=True)
class SimpleTypeBindingKey(BindingKey):
    type_: type
    tag: typing.Optional[str] = None

    def __post_init__(self):
        check_is_type_all_the_way_down(self.type_)


@dataclass(eq=True, frozen=True)
class ToDictBindingKey(BindingKey):
    dict_type: type
    key_value: typing.Union[type, str, int]
    tag: typing.Optional[str] = None

    def __post_init__(self):
        check_is_type_all_the_way_down(self.dict_type)
        assert typing.get_origin(self.dict_type) == dict
        assert typing.get_args(self.dict_type)[0] in {type, str, int}