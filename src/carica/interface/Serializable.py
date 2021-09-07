from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Union, Protocol, runtime_checkable

# All types acceptable as toml data
PrimativeType = Union[int, float, str, bool, List["PrimativeType"], Dict[str, "PrimativeType"], Set["PrimativeType"]] # type: ignore
# PrimativeType as a shallow set
primativeTypes = {int, float, str, bool, list, dict, set}


def objectIsShallowPrimative(o: Any) -> bool:
    """Decide if an object is a primative type, excluding any objects potentially contained within it.
    I.e:
    ```
    >>> objectIsShallowPrimative(1)
    True
    >>> class MyNonPrimativeClass:
    ...    pass
    ...
    >>> objectIsShallowPrimative(MyNonPrimativeClass())
    False
    >>> objectIsShallowPrimative([MyNonPrimativeClass()])
    True
    ```

    :param Any o: The object whose type to check
    :return: True if o itself is a primative type, False otherwise
    :rtype: bool
    """
    return any(isinstance(o, t) for t in primativeTypes)


def objectIsDeepPrimative(o: Any) -> bool:
    """Decide if a class is a primative type, including any objects potentially contained within it.
    I.e:
    ```
    >>> objectIsDeepPrimative(1)
    True
    >>> objectIsDeepPrimative([1])
    True
    >>> class MyNonPrimativeClass:
    ...    pass
    ...
    >>> objectIsDeepPrimative(MyNonPrimativeClass())
    False
    >>> objectIsDeepPrimative([MyNonPrimativeClass()])
    False
    ```

    This process is highly inefficient, as it recurses through all member objects in `o`.
    For a more efficient (but less confident) check, use `objectIsShallowPrimative` to check if just `o` itself is primative,
    excluding any member objects.

    :param Any o: The object whose type to check
    :return: True if o itself is a primative type, False otherwise
    :rtype: bool
    """
    if isinstance(o, list) or isinstance(o, set):
        return all(objectIsDeepPrimative(i) for i in o)
    elif isinstance(o, dict):
        return all(isinstance(k, str) and objectIsDeepPrimative(v) for k, v in o.items())
    else:
        return objectIsShallowPrimative(o)


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


    @classmethod
    @abstractmethod
    def deserialize(cls, data: PrimativeType, **kwargs) -> ISerializable:
        """Recreate a serialized ISerializable object

        :param PrimativeType data: A primative (likely a dictionary) containing all information needed to recreate the serialized object
        :return: A new object as specified by data
        :rtype: ISerializable
        """
        raise NotImplementedError()


# All types which are themselves primative, or can be serialized into primative types, as a shallow set
serializableTypes = primativeTypes.copy()
serializableTypes.add(SerializableType)


def objectIsShallowSerializable(o: Any) -> bool:
    """Decide if an object is a primative or serializable type, excluding any objects potentially contained within it.
    I.e:
    ```
    >>> objectIsShallowSerializable(1)
    True
    >>> class MySerializableClass:
    ...    def serialize(self, **kwargs):
    ...        return {}
    ...    def deserialize(self, data **kwargs):
    ...        return MySerializableClass()
    ...
    >>> objectIsShallowSerializable(MySerializableClass())
    True
    >>> class MyNonPrimativeClass:
    ...    pass
    ...
    >>> objectIsShallowSerializable(MyNonPrimativeClass())
    False
    >>> objectIsShallowSerializable([MyNonPrimativeClass()])
    True
    ```

    :param Any o: The object whose type to check
    :return: True if o itself is a primative or serializable type, False otherwise
    :rtype: bool
    """
    return any(isinstance(o, t) for t in serializableTypes)


def objectIsDeepSerializable(o: Any) -> bool:
    """Decide if a class is a primative or serializable type, including any objects potentially contained within it.
    I.e:
    ```
    >>> objectIsDeepSerializable(1)
    True
    >>> class MySerializableClass:
    ...    def serialize(self, **kwargs):
    ...        return {}
    ...    def deserialize(self, data **kwargs):
    ...        return MySerializableClass()
    ...
    >>> objectIsDeepSerializable(MySerializableClass())
    True
    >>> objectIsDeepSerializable([MySerializableClass()])
    True
    >>> class MyNonPrimativeClass:
    ...    pass
    ...
    >>> objectIsDeepSerializable(MyNonPrimativeClass())
    False
    >>> objectIsDeepSerializable([MyNonPrimativeClass()])
    False
    ```

    This process is highly inefficient, as it recurses through all member objects in `o`.
    For a more efficient (but less confident) check, use `objectIsShallowPrimative` to check if just `o` itself is primative,
    excluding any member objects.

    :param Any o: The object whose type to check
    :return: True if o itself is a primative type, False otherwise
    :rtype: bool
    """
    if isinstance(o, list) or isinstance(o, set):
        return all(objectIsDeepSerializable(i) for i in o)
    elif isinstance(o, dict):
        return all(isinstance(k, str) and objectIsDeepSerializable(v) for k, v in o.items())
    else:
        return objectIsShallowSerializable(o)
