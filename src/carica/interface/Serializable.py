from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Union, Protocol, runtime_checkable

PrimativeType = Union[int, float, str, bool, List["PrimativeType"], Dict[str, "PrimativeType"], Set["PrimativeType"]] # type: ignore


@runtime_checkable
class SerializableType(Protocol):
    """A type protocol representing any object with `serialize` and `deserialize` methods defined.
    Since this is a runtime checkable protocol class, isinstance() and issubclass() work for duck typing. That is,
    they will return true for classes with `serialize` and `deserialize` defined, even if the class does not inherit
    from `SerializableType`. For inheritence purposes, you may instead wish to use the `ISerializable` interface.
    """
    
    def serialize(self, **kwargs) -> PrimativeType:
        """Serialize this object into primative types (likely a dictionary, e.g JSON), to be recreated completely.

        :return: A primative (likely a dictionary) containing all information needed to recreate this object
        :rtype: PrimativeType
        """
        ...


    @classmethod
    def deserialize(cls, data: PrimativeType, **kwargs) -> SerializableType:
        """Recreate a serialized Serializable-like object

        :param PrimativeType data: A primative (likely a dictionary) containing all information needed to recreate the serialized object
        :return: A new object as specified by data
        :rtype: Serializable-like
        """
        ...


class ISerializable(ABC):
    """An object which can be represented entirely by a dictionary of primitives, created with the toDict method.
    This object can then be recreated perfectly using the fromDict method.
    """
    
    @abstractmethod
    def serialize(self, **kwargs) -> PrimativeType:
        """Serialize this object into primative types (likely a dictionary, e.g JSON), to be recreated completely.

        :return: A primative (likely a dictionary) containing all information needed to recreate this object
        :rtype: PrimativeType
        """
        raise NotImplementedError()


    @abstractmethod
    @classmethod
    def deserialize(cls, data: PrimativeType, **kwargs) -> ISerializable:
        """Recreate a serialized ISerializable object

        :param PrimativeType data: A primative (likely a dictionary) containing all information needed to recreate the serialized object
        :return: A new object as specified by data
        :rtype: ISerializable
        """
        raise NotImplementedError()