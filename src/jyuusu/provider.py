import typing
from abc import abstractmethod, ABC

from jyuusu.read_writer_monitor import ReadWriteMonitor

T = typing.TypeVar('T')


class Provider(ABC, typing.Generic[T]):
    @abstractmethod
    def get(self) -> T:
        pass


class Lazy(Provider[T]):
    def __init__(self, base_provider: Provider[T]):
        self.base_provider = base_provider
        self.read_write_monitor = ReadWriteMonitor()
        self.value: typing.Optional[T] = None

    def get(self) -> T:
        with self.read_write_monitor.read_session():
            value = self.value
        if value is not None:
            return value
        with self.read_write_monitor.write_session():
            if self.value is None:
                self.value = self.base_provider.get()
        return self.value

    @staticmethod
    def create(provider: Provider[T]) -> 'Lazy[T]':
        return Lazy(provider)


class InstanceProvider(Provider[T]):
    def __init__(self, value: T):
        self.value = value

    def get(self) -> T:
        return self.value
