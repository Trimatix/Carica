from dataclasses import Field, dataclass, _MISSING_TYPE, fields
from carica.interface import SerializableType, PrimativeType, primativeTypesTuple, SerializesToDict
from carica.typeChecking import objectIsShallowSerializable, objectIsDeepSerializable, _DeserializedTypeOverrideProxy, _CallableDeserializedTypeOverrideProxy
from carica.carica import BadTypeHandling, BadTypeBehaviour, ErrorHandling, VariableTrace, log, _serialize
from carica import exceptions
import typing
import traceback
from typing import Any, Dict, List, Mapping, Set, Tuple, Union, cast, TypeVar
# ignoring a warning here because private type _BaseGenericAlias can't be imported right now.
# it is a necessary import to unify over user-defined and special generics.
from typing import _BaseGenericAlias # type: ignore
import inspect

FIELD_TYPE_TYPES = (type, _BaseGenericAlias, TypeVar, _MISSING_TYPE)
FIELD_TYPE_TYPES_UNION = Union[type, _BaseGenericAlias, TypeVar, _MISSING_TYPE]
UNCASTABLE_TYPES = (Any, None)


def _handleTypeCasts(serializedValue: Any, fieldName: str,
                    possibleTypes: Union[FIELD_TYPE_TYPES_UNION, Tuple[FIELD_TYPE_TYPES_UNION]],
                    c_badTypeHandling: BadTypeHandling, _noLog: bool = False):

    def _log(*args, **kwargs):
        if not _noLog:
            log(*args, **kwargs)

    if not isinstance(possibleTypes, tuple):
        possibleTypes = (possibleTypes,)
    
    # Make sure the serialized type matches
    if not isinstance(serializedValue, cast(Tuple[type], possibleTypes)):
        fieldTypeError = f"Expected one of {'/'.join(str(t) for t in possibleTypes)} for field {fieldName}, " \
                        + f"but received serialized type {type(serializedValue).__name__}"

        # Attempt to cast incorrect types - useful, for example, for tuples (TOML only has lists)
        if c_badTypeHandling.behaviour == BadTypeBehaviour.CAST:
            # This is only used if there is only one potential type
            castException: Union[Exception, None] = None

            # Try to cast to each non-Any type
            for potentialType in possibleTypes:
                if potentialType not in UNCASTABLE_TYPES:
                    # We already know that potentialType is not a generic, but we also cannot cast to a TypeVar
                    if isinstance(potentialType, TypeVar):
                        _log(f"Ignoring potential field type {potentialType} - cannot construct TypeVar")
                        continue
                    potentialType = cast(type, potentialType)

                    # Attempt the cast
                    try:
                        newValue = potentialType(serializedValue)
                    # Failed, move onto the next type in the Union
                    except Exception as e:
                        castException = e
                        continue
                    # Cast was successful
                    else:
                        # Log it if required
                        if c_badTypeHandling.logSuccessfulCast:
                            _log(f"[WARNING] Successfully casted unexpected type for field {fieldName} from type " \
                                + f"{type(serializedValue).__name__} to {type(newValue).__name__}")
                        return newValue

            # No cast was successful.
            # Add exception trace if we have exactly one
            if castException is not None and c_badTypeHandling.includeExceptionTrace and len(possibleTypes) == 1:
                trace = traceback.format_exception(type(castException), castException, castException.__traceback__)
                fieldTypeError += f". Exception: {trace}"
            
            # If Any is allowed, just return the value without erroring
            if Any in possibleTypes:
                return serializedValue
            # Nothing to do if keeping failed field casts, except log if configured to
            elif c_badTypeHandling.keepFailedCast:
                if c_badTypeHandling.logTypeKeeping:
                    _log(f"[WARNING] Keeping original value for mistyped field following failed " \
                        + f"cast. {fieldTypeError}")
                return serializedValue
            # Throw errors if set to reject failed casts
            else:
                errMsg = f"Casting failed for unexpected type. {fieldTypeError}"
                if c_badTypeHandling.rejectType == ErrorHandling.RAISE:
                    raise TypeError(errMsg)
                elif c_badTypeHandling.rejectType == ErrorHandling.LOG:
                    _log(f"[WARNING] {errMsg}")

        # mismatched type behaviour is not CAST. Do nothing for KEEP except log if required
        elif c_badTypeHandling.behaviour == BadTypeBehaviour.KEEP:
            if c_badTypeHandling.logTypeKeeping:
                _log(f"[WARNING] Keeping mistyped field value: {fieldTypeError}")
            return serializedValue

        # Throw errors etc for REJECT handling
        elif c_badTypeHandling.behaviour == BadTypeBehaviour.REJECT:
            if c_badTypeHandling.rejectType == ErrorHandling.RAISE:
                raise TypeError(fieldTypeError)
            elif c_badTypeHandling.rejectType == ErrorHandling.LOG:
                _log(fieldTypeError)
            elif c_badTypeHandling.rejectType == ErrorHandling.IGNORE:
                pass
    
    # serialized value matches the expected types, do nothing
    else:
        return serializedValue


def _deserializeField(fieldName: str, fieldType: Union[type, _BaseGenericAlias, TypeVar, _MISSING_TYPE],
                        serializedValue: PrimativeType, c_variableTrace: VariableTrace = [],
                        c_badTypeHandling: BadTypeHandling = BadTypeHandling(), _noLog: bool = False,
                        deserializeSerializable: bool = True, **deserializerKwargs) -> Any:
    """Deserialize a serialized field value. This is a recursive function able to traverse the type hint tree of a field,
    and deserialize it as needed.

    :param str fieldName: The name of the field. Used for more helpful error messages.
    :param fieldType: The type hint of the field in the class, as given by SerializableDataClass._typeOfFieldNamed
    :type fieldType: Union[type, _BaseGenericAlias, TypeVar, _MISSING_TYPE]
    :param PrimativeType serializedValue: The value to deserialize into fieldType
    :param VariableTrace c_variableTrace: A trace of the variables that the carica deserializer traversed to reach this variable
    :param BadTypeHandling c_badTypeHandling: How to handle receiving toml variables that do not match the type of the
                                                python variable. See class for default values and value descriptions.
    :param bool deserializeValues: Whether to automatically deserialize serialized Serializable fields (Default True)
    :raise TypeError: If a field has invalid type hints, or serializedValue does not match fieldType
    :return: serializedValue, deserialized into fieldType
    """
    def _log(*args, **kwargs):
        if not _noLog:
            log(*args, **kwargs)

    # take any type if type hinted as such
    if fieldType in (Any, object):
        return serializedValue

    # Handle Union type hints
    # Ignoring a warning here for missing attribute __origin__ - i just checked for it!
    elif hasattr(fieldType, "__origin__") and fieldType.__origin__ is Union: # type: ignore
        # Get the generic parameters
        genericArgs = cast(Tuple[FIELD_TYPE_TYPES_UNION, ...], typing.get_args(fieldType))
        # Make sure the Union was parameterised
        if len(genericArgs) == 0:
            raise TypeError(f"Field {fieldName} is a generic type but has not been parameterised")

        optional = any(genericType is type(None) for genericType in genericArgs)
        
        # Handle optional hints
        if optional and serializedValue is None:
            return None
        
        for genericType in genericArgs:
            if genericType is not type(None):
                try:
                    _deserializeField(fieldName, genericType, serializedValue, c_variableTrace=c_variableTrace,
                                        c_badTypeHandling=c_badTypeHandling, _noLog=True, **deserializerKwargs)
                except:
                    pass
                else:
                    return _deserializeField(fieldName, genericType, serializedValue, c_variableTrace=c_variableTrace,
                                                c_badTypeHandling=c_badTypeHandling, **deserializerKwargs)
       
        # We can't cast to a union, and potential casts to parameterized types are handled in the _deserializeField call
        # Therefore, skip CAST behaviour and jump straight to checking for KEEP
        fieldTypeError = f"Expected one of {'/'.join(str(t) for t in genericArgs)} for field {fieldName}, " \
                        + f"but received serialized type {type(serializedValue).__name__}"

        if c_badTypeHandling.behaviour == BadTypeBehaviour.KEEP:
            if c_badTypeHandling.logTypeKeeping:
                _log(f"[WARNING] Keeping mistyped field value: {fieldTypeError}")
            return serializedValue

        if c_badTypeHandling.rejectType == ErrorHandling.RAISE:
            raise TypeError(fieldTypeError)
        elif c_badTypeHandling.rejectType == ErrorHandling.LOG:
            _log(fieldTypeError)
        elif c_badTypeHandling.rejectType == ErrorHandling.IGNORE:
            pass

    # If type hinted with a normal type or protocol
    elif isinstance(fieldType, type):
        # Deserialize if needed
        if issubclass(fieldType, SerializableType):
            if deserializeSerializable:
                return fieldType.deserialize(serializedValue, **deserializerKwargs)
            else:
                return serializedValue

        # Otherwise do nothing
        elif issubclass(fieldType, primativeTypesTuple):
            if isinstance(serializedValue, fieldType):
                return _handleTypeCasts(serializedValue, fieldName, fieldType, c_badTypeHandling)
            raise TypeError(f"Expected type of {fieldType} for field {fieldName}, " \
                            + f"but received serialized type {type(serializedValue).__name__}")

    # Handle generics other than Union (e.g List)
    elif isinstance(fieldType, _BaseGenericAlias):
        # Get the generic (e.g List, Dict...)
        # ignoring a warning here on missing attribute - I can't import _BaseGenericAlias, so the type hinter doesn't know that __origin__ is guaranteed
        generic: _BaseGenericAlias = fieldType.__origin__ # type: ignore
        # If the type hint is like a dict
        if issubclass(generic, Dict):
            # Make sure the serialized value matches
            if not isinstance(serializedValue, Dict):
                raise TypeError(f"Received serialized value for field {fieldName} of type {type(serializedValue).__name__}" \
                                + ", but expected dict")
            # get the type parameters
            genericArgs = cast(Tuple[FIELD_TYPE_TYPES_UNION, ...], typing.get_args(fieldType))
            # make sure parameters were supplied
            if len(genericArgs) == 0:
                raise TypeError(f"Field {fieldName} is a generic type but has not been parameterised")
            # make sure we're only expecting str keys
            if isinstance(genericArgs[0], type) and not issubclass(genericArgs[0], str):
                raise exceptions.NonStringMappingKey(fieldType, path=c_variableTrace,
                                                        extra=f"Field {fieldName} is typed as a dict with non-str keys")

            # deserialize the dict
            newValue = {}
            for k, v in cast(Dict[str, Any], serializedValue).items():
                newValue[k] = _deserializeField(fieldName, genericArgs[1], v,
                                                c_variableTrace=c_variableTrace + [k], c_badTypeHandling=c_badTypeHandling,
                                                **deserializerKwargs)
            return newValue

        # If the type hint is like a collection
        elif issubclass(generic, (List, Set, Tuple)):
            # Make sure the serialized type matches
            if not isinstance(serializedValue, (List, Set, Tuple)):
                raise TypeError(f"Expected type of {fieldType} for field {fieldName}, " \
                            + f"but received serialized type {type(serializedValue).__name__}")

            # get the type parameters
            genericArgs = cast(Tuple[FIELD_TYPE_TYPES_UNION, ...], typing.get_args(fieldType))
            # make sure parameters were supplied
            if len(genericArgs) == 0:
                raise TypeError(f"Field {fieldName} is a generic type but has not been parameterised")
            # make sure only one type was supplied
            if len(genericArgs) > 1 and genericArgs[1] is not Ellipsis:
                raise TypeError(f"Field {fieldName} is typed as a tuple with multiple type slots. " \
                                + "Tuples must be parameterised with a single type, or a type followed by ...")
            
            # deserialize each element in the collection in turn
            builder = (_deserializeField(fieldName, genericArgs[0], v, c_variableTrace=c_variableTrace + [i],
                                        c_badTypeHandling=c_badTypeHandling, **deserializerKwargs)
                        for i, v in enumerate(serializedValue)) # type: ignore
            hintedTypes = {List: list, Set: set, Tuple: tuple}
            if generic in hintedTypes:
                return hintedTypes[generic](builder)
            return generic(builder)
            
    # Failed to deserialize
    raise TypeError(f"Field {fieldName} is typed as a non-serializable type: {fieldType}")



@dataclass(init=True, repr=True, eq=True)
class SerializableDataClass(SerializesToDict):
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
        return {field.name: field for field in fields(cls)}


    @classmethod
    def _fieldNames(cls) -> List[str]:
        """Get a list of the field names defined in this class.

        :return: A list of the field names defined in the class.
        :rtype: List[str]
        """
        return list(cls._getFields().keys())


    def _fieldItems(self):
        """Get a `dict.items()`-style mapping of field names to field values.

        :return: a dictionary mapping field names to current values
        :rtype: Dict[str, Any]
        """
        return {k: getattr(self, k) for k in self._fieldNames()}.items() #self.__dataclass_fields__


    @classmethod
    def _typeOfFieldNamed(cls, fieldName: str) -> Union[type, _BaseGenericAlias, TypeVar, _MISSING_TYPE]:
        """Get the type annotation for the field with the given name. This does not consider type overriding.
        Be aware that type-hinting will cause this function to return a 'typing' type.

        :return: The type of the field called `fieldName`, or `dataclasses._MISSING_TYPE` if no type was given for the field
        :rtype: type
        """
        return cls._getFields()[fieldName].type


    @classmethod
    def _overriddenTypeOfFieldNamed(cls, fieldName: str) -> Union[type, _BaseGenericAlias, TypeVar, _MISSING_TYPE]:
        """Get the type annotation for the field with the given name, with awareness for overridden types.
        Be aware that type-hinting will cause this function to return a 'typing' type.

        :return: The (possibly overridden) type of the field called `fieldName`, or `dataclasses._MISSING_TYPE` if no type was given for the field
        :rtype: type
        """
        f = cls._getFields()[fieldName]
        if cls._fieldTypeIsOverridden(fieldName):
            if isinstance(f.default_factory, _CallableDeserializedTypeOverrideProxy):
                return cast(_CallableDeserializedTypeOverrideProxy, f.default_factory)._self__carica_uninitialized_type__
            return cast(_DeserializedTypeOverrideProxy, f.default)._self__carica_uninitialized_type__
        return f.type


    @classmethod
    def _fieldTypeIsOverridden(cls, fieldName: str) -> bool:
        """Decide whether the deserialized type for a field has been overridden.

        :return: True if the field called `fieldName` was marked with `TypeOverride`, False otherwise
        :rtype: type
        """
        f = cls._getFields()[fieldName]
        return isinstance(f.default, _DeserializedTypeOverrideProxy) or \
                isinstance(f.default_factory, _CallableDeserializedTypeOverrideProxy)


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

    
    def serialize(self, **kwargs) -> Dict[str, PrimativeType]:
        """Serialize this object into a dictionary, to be recreated completely.

        :return: A dictionary mapping field names to serialized values
        :rtype: Dict[str, PrimativeType]
        """

        return {k: _serialize(v) for k, v in self._fieldItems()}


    @classmethod
    def deserialize(cls, data: Mapping[str, PrimativeType], deserializeValues: bool = True, c_variableTrace: VariableTrace = [], **kwargs):
        """Recreate a serialized SerializableDataClass object. If `deserializeValues` is `True`,
        values fields which are serializable types will be automatically deserialized.

        :param Dict[str, PrimativeType] data: A dictionary mapping field names to values.
        :param bool deserializeValues: Whether to automatically deserialize serialized Serializable fields (Default True)
        :return: A new object as specified by data
        :rtype: SerializableDataClass
        """
        if not isinstance(data, dict):
            raise TypeError(f"Invalid serialized {cls.__name__}. Expected Dict[str, PrimativeType], received {type(data).__name__}")

        for k, v in data.items():
            if not isinstance(k, str):
                raise exceptions.NonStringMappingKey(k, path=c_variableTrace)
            data[k] = _deserializeField(k, cls._overriddenTypeOfFieldNamed(k), v, c_variableTrace=c_variableTrace + [k], 
                                        deserializeSerializable=deserializeValues, **kwargs)

        constructorArgs = inspect.signature(cls.__init__).parameters
        classKwargs = {k: v for k, v in kwargs.items() if k in constructorArgs}

        return cls(**data, **classKwargs)
