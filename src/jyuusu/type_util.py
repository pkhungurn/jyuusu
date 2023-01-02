from typing import Dict
import typing


def raise_type_assertion(type_, chain: typing.Optional[typing.List] = None):
    if chain is None:
        chain = []
    chain_str = ""
    for item in chain:
        chain_str += f"\n  {item}"
    raise AssertionError(f"{type_} is not a type.{chain_str}")


def assert_is_type(type_, chain: typing.Optional[typing.List] = None):
    if isinstance(type_, typing.ForwardRef):
        return
    if isinstance(type_, type):
        return
    #if isinstance(type_, GenericAlias):
    #    return
    if isinstance(type_, typing._GenericAlias):
        return
    raise_type_assertion(type_, chain)


def check_is_type_all_the_way_down(type_, chain: typing.Optional[typing.List] = None):
    if chain is None:
        chain = [type_]
    else:
        chain = chain + [type_]

    assert_is_type(type_, chain)
    origin = typing.get_origin(type_)
    if origin is None:
        return
    #elif origin is typing.Annotated:
    #    check_is_type_all_the_way_down(typing.get_args(type_)[0], chain)
    #    return
    args = typing.get_args(type_)
    for arg in args:
        check_is_type_all_the_way_down(arg, chain)


if __name__ == "__main__":
    check_is_type_all_the_way_down(Dict[int, str])
    check_is_type_all_the_way_down(typing.ForwardRef("T"))
    check_is_type_all_the_way_down(typing.List[typing.ForwardRef("T")])
    check_is_type_all_the_way_down(typing.Optional[typing.List[typing.ForwardRef("T")]])
    check_is_type_all_the_way_down(typing.Optional[typing.Dict[int, typing.ForwardRef("T")]])
    check_is_type_all_the_way_down(typing.Optional[typing.Dict[int, "B"]])
    #check_is_type_all_the_way_down(typing.Annotated[typing.Dict["A", str], "abc"])
