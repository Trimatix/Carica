from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, Iterable, Mapping, Type, TypeVar, Union, Protocol, runtime_checkable, Optional
from datetime import datetime

# All types acceptable as toml data. Tomlkit handles serializing of datetime objects automatically.
# Iterable includes set, list and tuple. It also includes dict and str!
# this type is Optional, because None is allowed in toml, but there is no NoneType exposed in python for use in the Union.
PrimativeType = Optional[Union[int, float, str, bool, datetime, Iterable["PrimativeType"], Mapping[str, "PrimativeType"]]]
# PrimativeType as a shallow set
primativeTypes = {int, float, str, bool, Iterable, Mapping, datetime, type(None)}
# PrimativeTypes as a shallow tuple
primativeTypesTuple = tuple(primativeTypes)

TClass = TypeVar("TClass")

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
    def deserialize(cls: Type[TClass], data: PrimativeType, **kwargs) -> TClass:
        """Recreate a serialized Serializable-like object

        :param PrimativeType data: A primative (likely a dictionary) containing all information needed to recreate the serialized object
        :return: A new object as specified by data
        :rtype: Serializable-like
        """
        ...
        

class ISerializable(ABC):
    """An object which can be represented entirely by a dictionary of primitives, created with the serialize method.
    This object can then be recreated perfectly using the deserialize method.
    """
    
    @abstractmethod
    def serialize(self, **kwargs) -> PrimativeType:
        """Serialize this object into primative types (likely a dictionary, e.g JSON), to be recreated completely.

        :return: A primative (likely a dictionary) containing all information needed to recreate this object
        :rtype: PrimativeType
        """
        raise NotImplementedError()


    @classmethod
    @abstractmethod
    def deserialize(cls: Type[TClass], data: PrimativeType, **kwargs) -> TClass:
        """Recreate a serialized ISerializable object

        :param PrimativeType data: A primative (likely a dictionary) containing all information needed to recreate the serialized object
        :return: A new object as specified by data
        :rtype: ISerializable
        """
        raise NotImplementedError()
    

# All types which are themselves primative, or can be serialized into primative types, as a shallow set
serializableTypes = primativeTypes.copy()
serializableTypes.add(SerializableType)
serializableTypesTuple = tuple(serializableTypes)

TClass = TypeVar("TClass")
TSerialized = TypeVar("TSerialized", bound=PrimativeType)

class SerializesToType(SerializableType, Generic[TSerialized]):
    def serialize(self, **kwargs) -> TSerialized: ...

    @classmethod
    def deserialize(cls: Type[TClass], data: TSerialized, **kwargs) -> TClass: ...

SerializesToDict = SerializesToType[Mapping[str, PrimativeType]]
