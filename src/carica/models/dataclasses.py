from dataclasses import Field, dataclass, _MISSING_TYPE
from carica.interface import SerializableType, ISerializable, PrimativeType, primativeTypesTuple
from carica.typeChecking import objectIsShallowSerializable, objectIsDeepSerializable, objectIsShallowPrimative
import typing
from typing import Any, Dict, List, Mapping, Optional, Protocol, Set, Tuple, Union, cast, TypeVar
from typing import _BaseGenericAlias # type: ignore

FIELD_TYPE_TYPES = (type, _BaseGenericAlias, TypeVar, _MISSING_TYPE)

def _deserializeField(fieldName: str, fieldType: Union[type, _BaseGenericAlias, TypeVar, _MISSING_TYPE],
                        serializedValue: PrimativeType, **deserializerKwargs) -> Any:
    """Deserialize a serialized field value. This is a recursive function able to traverse the type hint tree of a field,
    and deserialize it as needed.

    :param str fieldName: The name of the field. Used for more helpful error messages.
    :param fieldType: The type hint of the field in the class, as given by SerializableDataClass._typeOfFieldNamed
    :type fieldType: Union[type, _BaseGenericAlias, TypeVar, _MISSING_TYPE]
    :param PrimativeType serializedValue: The value to deserialize into fieldType
    :raise TypeError: If a field has invalid type hints, or serializedValue does not match fieldType
    :return: serializedValue, deserialized into fieldType
    """
    # take any type if type hinted as such
    if fieldType in (Any, object):
        return serializedValue

    # Handle Union type hints
    elif hasattr(fieldType, "__origin__") and fieldType.__origin__ is Union: # type: ignore
        # Get the generic parameters
        genericArgs = typing.get_args(fieldType)
        # Make sure the Union was parameterised
        if len(genericArgs) == 0:
            raise TypeError(f"Field {fieldName} is a generic type but has not been parameterised")

        # Make sure the Union was only parameterised with primative types
        for genericType in genericArgs:
            if isinstance(genericType, _BaseGenericAlias):
                raise TypeError(f"Field {fieldName} is typed as a Union with a generic parameter")
            if not isinstance(genericType, primativeTypesTuple):
                raise TypeError(f"Field {fieldName} is typed as a Union with a non-primative parameter")
        
        # Make sure the serialized type matches
        if not isinstance(serializedValue, genericArgs):
            raise TypeError(f"Expected one of {'/'.join(t.__name__ for t in genericArgs)} for field {fieldName}, " \
                            + f"but received serialized type {type(serializedValue).__name__}")
        # Do nothing
        return serializedValue

    # Handle Optional type hints
    elif hasattr(fieldType, "__origin__") and fieldType.__origin__ is Optional: # type: ignore
        # Get the generic parameters
        genericArgs = typing.get_args(fieldType)
        # Make sure the Union was parameterised
        if len(genericArgs) == 0:
            raise TypeError(f"Field {fieldName} is a generic type but has not been parameterised")
        
        # Accept None
        if serializedValue is None:
            return None
        else:
            # Otherise require the parameter type
            return _deserializeField(fieldName, genericArgs[0], serializedValue, **deserializerKwargs)

    # If type hinted with a normal type or protocol
    elif isinstance(fieldType, type):
        # Deserialize if needed
        if issubclass(fieldType, SerializableType):
            return fieldType.deserialize(serializedValue, **deserializerKwargs)
        # Otherwise do nothing
        elif issubclass(fieldType, primativeTypesTuple):
            if isinstance(serializedValue, fieldType):
                return serializedValue
            raise TypeError(f"Expected type of {fieldType} for field {fieldName}, " \
                            + f"but received serialized type {type(serializedValue).__name__}")

    # Handle generics other than Union (e.g List)
    elif isinstance(fieldType, _BaseGenericAlias):
        # Get the generic (e.g List, Dict...)
        generic: _BaseGenericAlias = fieldType.__origin__
        # If the type hint is like a dict
        if issubclass(generic, typing.Mapping):
            # Make sure the serialized value matches
            if not isinstance(serializedValue, Mapping):
                raise TypeError(f"Received serialized value for field {fieldName} of type {type(serializedValue).__name__}" \
                                + ", but expected dict")
            # get the type parameters
            genericArgs = typing.get_args(fieldType)
            # make sure parameters were supplied
            if len(genericArgs) == 0:
                raise TypeError(f"Field {fieldName} is a generic type but has not been parameterised")
            # make sure we're only expecting str keys
            if not issubclass(genericArgs[0], str):
                raise TypeError(f"Field {fieldName} is typed as a dict with non-str keys")

            # deserialize the dict
            newValue = {}
            for k, v in cast(Mapping[str, Any], serializedValue).items():
                newValue[k] = _deserializeField(fieldName, genericArgs[1], v, **deserializerKwargs)
            return newValue

        # If the type hint is like a collection
        elif issubclass(generic, (List, Set, Tuple)): # type: ignore
            # Make sure the serialized type matches
            if not isinstance(serializedValue, (List, Set, Tuple)): # type: ignore
                raise TypeError(f"Expected type of {fieldType} for field {fieldName}, " \
                            + f"but received serialized type {type(serializedValue).__name__}")

            # get the type parameters
            genericArgs = typing.get_args(fieldType)
            # make sure parameters were supplied
            if len(genericArgs) == 0:
                raise TypeError(f"Field {fieldName} is a generic type but has not been parameterised")
            # make sure only one type was supplied
            if len(genericArgs) > 1 and genericArgs[1] is not Ellipsis:
                raise TypeError(f"Field {fieldName} is typed as a tuple with multiple type slots. " \
                                + "Tuples must be parameterised with a single type, or a type followed by ...")

            # deserialize each element in the collection in turn
            builder = (_deserializeField(fieldName, genericArgs[0], v) for v in serializedValue) # type: ignore
            hintedTypes = {List: list, Set: set, Tuple: tuple}
            if generic in hintedTypes:
                return hintedTypes[generic](builder)
            return generic(builder)
            
    # Failed to deserialize
    raise TypeError(f"Field {fieldName} is typed as a non-serializable type: {fieldType}")

    


@dataclass(init=True, repr=True)
class SerializableDataClass(ISerializable):
    """An dataclass with added serialize/deserialize methods.
    Values stored in the fields of the dataclass are not type checked, but must be primatives/serializable for the serialize
    method to return valid results.

    Subclasses of SerializableDataClass *must* be decorated with `@dataclasses.dataclass` to function properly.
    """
    @classmethod
    def _getFields(cls) -> Dict[str, Field]:
        """Get the `@dataclass`-generated mapping of field names to `Field`s.
        Separating this method out to isolate mypy warnings.

        :return: A dictionary mapping field names to `dataclasses.Field`
        :rtype: Dict[str, Field]
        """
        return cls.__dataclass_fields__ # type: ignore


    @classmethod
    def _fieldNames(cls) -> List[str]:
        """Get a list of the field names defined in this class.

        :return: A list of the field names defined in the class.
        :rtype: List[str]
        """
        return list(cls._getFields().keys())


    def _fieldItems(self) -> Dict[str, Any]:
        """Get a `dict.items()`-style mapping of field names to field values.

        :return: a dictionary mapping field names to current values
        :rtype: Dict[str, Any]
        """
        return {k: getattr(self, k) for k in self._fieldNames()}


    @classmethod
    def _typeOfFieldNamed(cls, fieldName: str) -> Union[type, _BaseGenericAlias, TypeVar, _MISSING_TYPE]:
        """Get the type annotation for the field with the given name.
        Be aware that type-hintig will cause this function to return a 'typing' type - either a `_GenericAlias` for generics,
        or `TypeVar` for non-generics.

        :return: The type of the field called `fieldName`, or `dataclasses._MISSING_TYPE` if no type was given for the field
        :rtype: type
        """
        return cls._getFields()[fieldName].type


    @classmethod
    def _hasISerializableOrGenericField(cls) -> bool:
        """Decide whether this class has any fields which are Serializable or generic types.
        If any fields are themselves Serializable types, then we know that we need to traverse the field types tree when
        deserializing to receive proper types. If any fields are generic, then we do not immediately know if any Serializable
        generics exist without traversing the field types tree. If we're doing that, then we might as well deserialize while
        we do it!

        :return: False if we are immediately sure no fields contain Serializable types, True otherwise
        :rtype: bool
        """
        for fieldName in cls._fieldNames():
            fieldType = cls._typeOfFieldNamed(fieldName)
            if not isinstance(fieldType, _MISSING_TYPE):
                if isinstance(fieldType, type):
                    if issubclass(fieldType, SerializableType):
                        return True

                elif isinstance(fieldType, _BaseGenericAlias):
                    return True

                elif isinstance(fieldType, TypeVar):
                    if isinstance(fieldType, SerializableType):
                        return True
        
        return False

    
    def serialize(self, deepTypeChecking: bool = False, **kwargs) -> Dict[str, PrimativeType]:
        """Serialize this object into a dictionary, to be recreated completely.

        :param bool deepTypeChecking: Whether to ensure serializability of member objects recursively (Default False)
        :return: A dictionary mapping field names to serialized values
        :rtype: Dict[str, PrimativeType]
        """
        data: Dict[str, PrimativeType] = {}

        for k in self._getFields():
            v = getattr(self, k)
            if isinstance(v, SerializableType):
                data[k] = v.serialize(**kwargs)
            elif not objectIsShallowSerializable(v):
                raise TypeError(f"Field '{k}' is of non-serializable type: {type(v).__name__}")
            elif deepTypeChecking and not objectIsDeepSerializable(v):
                raise TypeError(f"Field '{k}' has a non-serializable member object")
            else:
                data[k] = v

        return data


    @classmethod
    def deserialize(cls, data, deserializeValues: bool = True, **kwargs) -> "SerializableDataClass":
        """Recreate a serialized SerializableDataClass object. If `deserializeValues` is `True`,
        values fields which are serializable types will be automatically deserialized.

        :param Dict[str, PrimativeType] data: A dictionary mapping field names to values.
        :param bool deserializeValues: Whether to automatically deserialize serialized Serializable fields (Default True)
        :return: A new object as specified by data
        :rtype: SerializableDataClass
        """
        if not isinstance(data, dict):
            raise TypeError(f"Invalid type for parameter data. Expected Dict[str, PrimativeType], received {type(data).__name__}")

        if deserializeValues and cls._hasISerializableOrGenericField():
            for k, v in data.items():
                if not isinstance(k, str):
                    raise TypeError(f"Invalid serialized {cls.__name__} key '{k}' Expected str, received {type(data).__name__}")
                data[k] = _deserializeField(k, cls._typeOfFieldNamed(k), v, **kwargs)

        return cls(**data, **kwargs) # type: ignore
