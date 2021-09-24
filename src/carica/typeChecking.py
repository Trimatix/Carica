from typing import Any, List, Union
from carica.interface import primativeTypes, serializableTypes
from carica import exceptions


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


def raiseForShallowNonSerializable(o: Any) -> None:
    """The same as objectIsShallowSerializable, but with different return semantics:
    If `o` is shallow serializable, None is returned.
    If `o` is shallow non-serializable an exception is raised with details of the reasoning.

    :param Any o: The object whose type to check
    :raise exceptions.NonSerializableObject: If o is itself a non-serializable type
    :raise exceptions.NonStringMappingKey: If o is a mapping containing a non-str key
    """
    if isinstance(o, dict):
        for k in o:
            if not isinstance(k, str):
                raise exceptions.NonStringMappingKey(k)
    elif not objectIsShallowSerializable(o):
        raise exceptions.NonSerializableObject(o)


def _recurseRaiseForDeepNonSerializable(o: Any, depth: int, path: List[Union[str, int]]) -> None:
    """Internal recursive method for use exclusively by raiseForDeepNonSerializable.
    """
    if isinstance(o, list) or isinstance(o, set):
        for i in o:
            _recurseRaiseForDeepNonSerializable(i, depth+1, path + [i])
    elif isinstance(o, dict):
        for k, v in o.items():
            if not isinstance(k, str):
                raise exceptions.NonStringMappingKey(k, depth, path)
            _recurseRaiseForDeepNonSerializable(v, depth+1, path + [k])
    else:
        if not objectIsShallowSerializable(o):
            raise exceptions.NonSerializableObject(o, depth, path)


def raiseForDeepNonSerializable(o: Any) -> None:
    """The same as objectIsDeepSerializable, but with different return semantics:
    If `o` is completely serializable, None is returned.
    If `o` is non-serializable or contains a non-serializable member object, an exception is raised with details of
    the reasoning.

    This process is highly inefficient, as it recurses through all member objects in `o`.
    For a more efficient (but less confident) check, use `raiseForShallowNonSerializable` to check if just `o` itself is
    serializable, excluding any member objects.

    :param Any o: The object whose type to check
    :raise exceptions.NonSerializableObject: If a non-serializable object is encountered at any level
    :raise exceptions.NonStringMappingKey: If a non-str mapping key is encountered at any level
    """
    _recurseRaiseForDeepNonSerializable(o, 0, [])