from enum import Enum
from types import ModuleType
import tomlkit
from tomlkit.container import Container as TKContainer
from tomlkit import items as TKItems
import os
from typing import Any, Dict, List, Protocol, Union, Iterable, Mapping, cast, runtime_checkable
import tokenize

from tomlkit.toml_document import TOMLDocument
from carica.interface import SerializableType, PrimativeType
from carica.typeChecking import objectIsShallowPrimative, _DeserializedTypeOverrideProxy, TypeHint
from carica import exceptions
from carica.util import INCOMPATIBLE_TOML_TYPES, convertIncompatibleTomlTypes
from dataclasses import dataclass
import traceback

CFG_FILE_EXT = ".toml"
DISALLOWED_TOKEN_TYPES = {tokenize.INDENT}
DISALLOWED_TOKEN_TYPE_VALUES = {tokenize.NAME: {"from", "import"}}
LINE_DELIMITER_TOKEN_TYPES = {tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER}
IGNORED_TOKEN_TYPES = {tokenize.DEDENT}

VariableTrace = List[Union[int, str]]


def log(msg):
    print(msg)


def formatException(e, includeTrace):
    if includeTrace:
        return "".join(traceback.format_exception(type(e), e, e.__traceback__))
    return str(e)


def tokenDisallowed(token: tokenize.TokenInfo) -> bool:
    """Decide whether or not a token can be present in avariable assignment line.
    The return value is the inverse of what you would expect: True if the token can NOT be part of a variable assignment line.

    :param tokenize.TokenInfo token: The token to check
    :return: True if the token is an ILLEGAL part of a variable assignment, False if the token is LEGAL.
    :rtype: bool
    """
    return token.type in DISALLOWED_TOKEN_TYPES or \
        (token.type in DISALLOWED_TOKEN_TYPE_VALUES and token.string in DISALLOWED_TOKEN_TYPE_VALUES[token.type])


def lineStartsWithVariableIdentifier(line: List[tokenize.TokenInfo]) -> bool:
    """Decide if a series of tokens starts with a variable identifier.
    This is a large estimation.
    """
    return len(line) > 1 \
        and line[0].type == tokenize.NAME \
        and line[1].type == tokenize.OP and line[1].string == "="


@dataclass
class ConfigVariable:
    name: str
    value: Any
    inlineComments: List[str]
    preComments: List[str]
    loadedType: TypeHint


    def hasInline(self):
        return self.inlineComments != []


    def hasPre(self):
        return self.preComments != []


@runtime_checkable
class _TKItemWithValue(Protocol):
    def value(self): ...


def _partialModuleVariables(module: ModuleType) -> Dict[str, ConfigVariable]:
    """Estimate The set of variables defined in the given module.
    Attempts to ignore other name types, such as functions, classes and imports.
    Names cannot be indented, and multiple assignment is not supported - variable declarations must be on their own lines.

    The resulting dictionary maps variable names to a data class containing the variable name, value, inline comment(s),
    and preceeding comments. Inline comments can be multiple if the variable was assigned to a second time with a new inline
    comment. A comment 'preceeds' a variable if it is present either on the line before the variable, or on the line before
    a preceeding comment of the variable.

    This function simply iterates over the module's tokens, and does not build an AST.
    This means that certain name definition structures will result in false positives/negatives.
    This behaviour has not been extensively tested, but once such false positive has been identified:
    When invoking a callable (such as a class or function) with a keyword argument on a new, unindented line, the argument
    name will be falsely identified as a variable name. E.g:
    ```
    my_variable = dict(key1=value1,
    key2=value2)
    ```
    produces `my_variable` and `key2` as variable names.

    :param ModuleType module: The module from which to estimate variable names
    :return: An estimated dict of variables defined in module. See above for details and limitations.
    :rtype: Dict[str, ConfigVariable]
    """
    # TODO: Ignoring a warning here because virtual modules are not supported yet
    with tokenize.open(module.__file__) as f: # type: ignore[reportGeneralTypeIssues]
        tokens = tokenize.generate_tokens(f.readline)
        # All detected variables
        moduleVariables: Dict[str, ConfigVariable] = {}
        # All tokens on the current line
        currentLine: List[tokenize.TokenInfo] = []
        # Track consecutive lines of comments, in case they preceed a variable
        commentsQueue: List[str] = []

        ignoreLine = False
        
        # Iterate over all tokens in the file. tokenizer doesn't split by new line for us, so we'll have to do it manually.
        for token in tokens:
            # If the current line is to be ignored
            if ignoreLine:
                # Continue iterating until a new line character is found, then stop and go back to normal parsing
                if token.type == tokenize.NEWLINE:
                    ignoreLine = False
                continue

            # Filter out lines that start with a token that eliminates the possiblity of this line defining a variable
            if currentLine == [] and tokenDisallowed(token):
                # Set line ignore flag
                if token.type != tokenize.NEWLINE:
                    ignoreLine = True
                # Clear the preceeding comments queue
                if commentsQueue:
                    commentsQueue.clear()
                # Proceed to the next line of code
                continue
            
            # End of line reached?
            elif token.type in LINE_DELIMITER_TOKEN_TYPES:
                # Were there any tokens on the line?
                if currentLine:
                    # This check needs to be performed before clearing the preceeding comments queue,
                    # As it checks if the new line breaks a series of comments. I might as well put the
                    # variable registering logic in here as well, because it also can only happen if the
                    # line did not start with a comment, and it also calls for clearing the preeding comments queue.
                    if currentLine[0].type != tokenize.COMMENT:
                        # Was the first token on the line a variable identifier? *This is the estimation bit*
                        if lineStartsWithVariableIdentifier(currentLine):
                            # Store a record of the variable
                            variableName = currentLine[0].string
                            if variableName not in moduleVariables:
                                # Plaster solution to ignore false positives
                                try:
                                    variableValue = getattr(module, variableName)
                                except AttributeError:
                                    # This variable name must be a false positive.
                                    # Clear the preceeding comments queue, and move onto the next line
                                    if commentsQueue:
                                        commentsQueue.clear()
                                    currentLine = []
                                    continue
                                
                                # Variable value was fetched successfully, record it
                                loadedType = variableValue._self__carica_uninitialized_type__ if isinstance(variableValue, _DeserializedTypeOverrideProxy) else type(variableValue)
                                moduleVariables[variableName] = ConfigVariable(variableName, variableValue, [], [], loadedType)

                            # Record any preceeding comments
                            if commentsQueue:
                                moduleVariables[variableName].preComments += commentsQueue

                        # Clear the preceeding comments queue
                        if commentsQueue:
                            commentsQueue.clear()

                    # Move onto the next line
                    currentLine = []
                
                # No tokens on the line, breaking any series of comments. Clear the preceeding comments queue
                elif commentsQueue:
                    commentsQueue.clear()

            # Is this a comment?
            elif token.type == tokenize.COMMENT:
                # Is it an inline comment?
                if currentLine != []:
                    # Does this line declare a variable?
                    if lineStartsWithVariableIdentifier(currentLine):
                        variableName = currentLine[0].string

                        # Create a record for the variable if none exists
                        if variableName not in moduleVariables:
                            variableValue = getattr(module, variableName)
                            loadedType = variableValue._self__carica_uninitialized_type__ if isinstance(variableValue, _DeserializedTypeOverrideProxy) else type(variableValue)
                            moduleVariables[variableName] = ConfigVariable(variableName, variableValue, [], [], loadedType)

                        # Record the found inline comment
                        moduleVariables[variableName].inlineComments.append(token.string.lstrip("# "))
                
                # Is it a comment line?
                else:
                    # Add the comment text to the preceeding comments queue
                    commentsQueue.append(token.string.lstrip("# "))
                    currentLine.append(token)

            # No processing of this token to be performed, record it and move onto the next one in the line
            elif token.type not in IGNORED_TOKEN_TYPES:
                currentLine.append(token)
        
    return moduleVariables


def _serialize(o: Any, path: VariableTrace, depthLimit=20, serializerKwargs={}) -> PrimativeType:
    """Internal recursive method to serialize any serializable object, or throw exceptions with useful key trace info
    """
    # Check recursion depth
    if len(path) > depthLimit:
        raise RecursionError()

    # o is directly serializable, serialize it and return that
    if isinstance(o, SerializableType):
        return _serialize(o.serialize(**serializerKwargs), path + ["[serialize]"], depthLimit=depthLimit,
                            serializerKwargs=serializerKwargs)

    # o is a mapping, serialize each value
    elif isinstance(o, Mapping):
        serializedDict: Dict[str, PrimativeType] = {}
        for k, v in o.items():
            # ensure keys are str
            if not isinstance(k, str):
                raise exceptions.NonStringMappingKey(k, len(path)-1, path)

            serializedDict[k] = _serialize(v, path + [k], depthLimit=depthLimit, serializerKwargs=serializerKwargs)
        return serializedDict

    # o is an iterable, serialize each element
    if isinstance(o, Iterable) and not isinstance(o, str):
        serializedList: List[PrimativeType] = []
        for i in o:
            serializedList.append(_serialize(i, path + [i], depthLimit=depthLimit, serializerKwargs=serializerKwargs))
        
        # ensure serialized lists contain either tables or non-dict primatives, but not both
        if len(serializedList) > 1:
            if (isinstance(serializedList[0], Mapping) and any(not isinstance(i, Mapping) for i in serializedList[1:])) or \
                    (not isinstance(serializedList[0], Mapping) and any(isinstance(i, Mapping) for i in serializedList[1:])):
                raise exceptions.MultiTypeList(o, len(path)-1, path)

        return serializedList

    # o is just a normal primative, return it as is
    elif objectIsShallowPrimative(o):
        return o

    # unable to match serializing method, exception time
    raise exceptions.NonSerializableObject(o, len(path)-1, path)


def makeDefaultCfg(cfgModule: ModuleType, fileName: str = "defaultCfg" + CFG_FILE_EXT, retainComments: bool = True,
                    **serializerKwargs) -> str:
    """Create a config file containing all configurable variables with their default values.
    The name of the generated file may optionally be specified.

    fileName may also be a path, either relative or absolute. If missing directories are specified
    in fileName, they will be created.

    If fileName already exists, then the generated file will be renamed with an incrementing number extension.

    This method has the option to retain variable 'docstrings' - comments which Carica deems to belong to a variable.
    A comment may belong to a variable if it is one of:
        a) On the same line as the variable declaration (an 'inline comment')
        b) A line comment on the line immediately preceeding the variable declaration (a 'preceeding comment')
        c) A line comment on the line immediately preceeding an existing preceeding comment, allowing for multi-line comments

    Retaining of preceeding comments is currently disabled. This is due to the TOML spec's standards for variable ordering
    within a document being stricter than python's, leading to list and dict preceeding comments appearing in odd places.
    This is currently in the process of being worked around.

    :param ModuleType cfgModule: Module to convert to toml
    :param str fileName: Path to the file to generate (Default "defaultCfg.toml")
    :param bool retainComments: Whether or not to write variable docstrings to the config (Default True)
    :return: path to the generated config file
    :rtype: str
    :raise ValueError: If fileName does not end in CFG_FILE_EXT
    """
    # Ensure fileName is toml
    if not fileName.endswith(CFG_FILE_EXT):
        raise ValueError("file name must end with " + CFG_FILE_EXT)

    # Create missing directories
    fileName = os.path.abspath(os.path.normpath(fileName))
    if not os.path.isdir(os.path.dirname(fileName)):
        os.makedirs(os.path.dirname(fileName))

    # If fileName already exists, make a new one by adding a number onto fileName.
    fileName = fileName.split(CFG_FILE_EXT)[0]
    cfgPath = fileName
    
    currentExt = 0
    while os.path.exists(cfgPath + CFG_FILE_EXT):
        currentExt += 1
        cfgPath = fileName + "-" + str(currentExt)

    cfgPath += CFG_FILE_EXT

    # Read default config values
    defaults = _partialModuleVariables(cfgModule)

    # Make a document to populate
    newDoc = tomlkit.document()

    # Iterate over all variables in the module
    for varName, var in defaults.items():
        # Preceeding comments are currently disabled, while variable reordering is worked around
        """
        # Does the variable have any preceeding comments?
        if retainComments and var.hasPre():
            # Add a new line, just for readability
            newDoc.add(tomlkit.nl())
            # Add all preceeding comments
            for prevDoc in var.preComments:
                newDoc.add(tomlkit.comment(prevDoc))
        """

        # Serialize the variable if required, and write it to the doc
        newDoc[varName] = _serialize(var.value, [varName], serializerKwargs=serializerKwargs)

        # Does the variable have any preceeding comments?
        if retainComments and var.hasInline():
            # Add all inline comments
            for inDoc in var.inlineComments:
                if type(newDoc[varName]) == TKContainer:
                    raise RuntimeError(f"Attempted to add a comment to a tomlkit.container.Container: {varName}")
                cast(TKItems.Item, newDoc[varName]).comment(inDoc)

    # Dump to toml and write to file
    with open(cfgPath, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(newDoc).lstrip("\n"))

    # log and return path to new file
    log("Created " + cfgPath)
    return cfgPath


class BadTypeBehaviour(Enum):
    """Configure how to handle receiving variable values in toml that are of a different type to the corresponding
    variable in the python module.
    
    Values:
    - REJECT: Reject the value, falling back on ErrorHandling behaviour
    - KEEP: Ignore type discrepencies, and just pass the variable into the python module regardless
    - CAST: Attempt to cast the incorrectly-typed value with a call the correct type.
            E.g if the variable is of type float in python, but int is received from TOMl, this behaviour will call float(x)
            Where x is the value given in TOML
    """
    REJECT = 1
    KEEP = 2
    CAST = 3


class ErrorHandling(Enum):
    """Configure how to handle errors. Refer to the usage context of this class for the specific behaviour that will
    resut from this setting.
    
    Values:
    - RAISE: Raise an exception
    - LOG: Log the error without throwing an exception
    - IGNORE: Do nothing
    """
    RAISE = 1
    LOG = 2
    IGNORE = 3


@dataclass
class BadTypeHandling:
    """Configure how Carica should handle receiving variable values in toml that are of a different type to the corresponding
    variable in the python module, and details of logging for these events.

    The `behaviour` field sets how Carica should handle variable types in TOML that do not match the type expected by the
    python module. This allows for automatic type casting, which can be especially useful for primative types, for example:
    If the python module contains a variable that is of type `float`, but the variable is given as an `int` in toml,
    `BadTypeBehaviour.CAST` will cast the toml-given value to `float` using the `float(x)` constructor.

    The `rejectType` field sets how Carica should handle variable type rejections. If `behaviour` is `REJECT`, should
    an exception be thrown, or a log created, or neither?

    The `keepFailedCast` field is used where `behaviour` is `CAST`, setting whether to keep or reject values which fail
    casting. If an exception occurs when attempting to cast (e.g an appropriate constructor does not exist), then
    `keepFailedCast` triggers the following:
     - When `True`, keep the value from before the attempted cast, and pass this (wrongly typed) value to the python module
     - When `False`, reject this value, falling back on `rejectType` behaviour

    The `logTypeKeeping` field sets whether the keeping of variables of mismatched types should be logged. This field is used
    in two cases:
        - If `behaviour` is `KEEP`, and a value of a mismatched type is encountered
        - If `behaviour` is `CAST`, `keepFailedCast` is `True`, and a value fails type casting

    In either of these cases, if `logTypeKeeping` is `True`, a log will be created of the event. Otherwise, the value will be
    kept silently.

    The `logSuccessfulCast` field sets whether to create a log message in the event of a type-mismatched variable being casted
    to the correct type successfully. This field is only of use where `behaviour` is `CAST`.

    The `includeExceptionTrace` field sets whether exception logging should include the exception trace.

    :var behaviour: Enum setting how to handle mismatched variable types. See class for value descriptions (Default CAST)
    :vartype behaviour: BadTypeBehaviour
    :var rejectType: Enum setting the handling for the above type rejections. See class for value descriptions (Default RAISE)
    :vartype rejectType: ErrorHandling
    :var keepFailedCast: Whether to reject values that failed casting, or fall back to keeping the original (Default False)
    :vartype keepFailedCast: bool
    :var logTypeKeeping: Whether to log keeping of mismatched variable types or do so silently (Default True)
    :vartype logTypeKeeping: bool
    :var logSuccessfulCast: Whether to log successful casts of mismatched variable types (Default True)
    :vartype logSuccessfulCast: bool
    :var includeExceptionTrace: Whether to include the trace of logged exceptions, e.g in `keepFailedCast` (Default False)
    :vartype includeExceptionTrace: bool
    """
    behaviour = BadTypeBehaviour.CAST
    rejectType = ErrorHandling.RAISE
    keepFailedCast = False
    logTypeKeeping = True
    logSuccessfulCast = True
    includeExceptionTrace = False


def loadCfg(cfgModule: ModuleType, cfgFile: str, badTypeHandling: BadTypeHandling = BadTypeHandling(),
            badNameHandling: ErrorHandling = ErrorHandling.RAISE):
    """Load the values from a specified config file into attributes of the python cfg module.
    All config attributes are optional, but if a mapping is given, all desired values must be set.

    :param ModuleType cfgModule: Module to load variable values into
    :param str cfgFile: Path to the file to load. Can be relative or absolute
    :param ErrorHandling badNameHandling: How to handle variables from cfgFile which are not named in cfgModule. See class
                                            for default value and value descriptions.
    :param BadTypeHandling badTypeHandling: How to handle receiving toml variables that do not match the type of the
                                            python variable. See class for default values and value descriptions.
    :raise ValueError: When cfgFile is of an unsupported format
    """
    # Ensure the given config is toml
    if not cfgFile.endswith(CFG_FILE_EXT):
        raise ValueError("config files must be TOML")

    # Load from toml to dictionary
    with open(cfgFile, "r", encoding="utf-8") as f:
        config = tomlkit.loads(f.read())

    # Read default config values
    defaults = _partialModuleVariables(cfgModule)

    # Assign config values to cfg attributes
    for varName in config:
        varName = cast(str, varName)
        # Validate attribute names
        if varName not in defaults:
            if badNameHandling == ErrorHandling.RAISE:
                raise NameError(f"Unrecognised config variable name: {varName}")
            elif badNameHandling == ErrorHandling.LOG:
                log(f"[WARNING] Ignoring unrecognised config variable name: {varName}")

        else:
            # Get the type of the default value (or the type override) for this variable
            defaultType = defaults[varName].loadedType

            # Get the value for the variable that is defined in the config file
            # This check ignores any config attributes that do not have a value, for example comments and whitespace.
            if isinstance(config[varName], _TKItemWithValue):
                newValue: Any = cast(_TKItemWithValue, config[varName]).value
            else:
                continue

            # Convert incompatible types, e.g TOMLDocument
            if isinstance(newValue, INCOMPATIBLE_TOML_TYPES):
                newValue = convertIncompatibleTomlTypes(newValue)

            # deserialize serializable variables
            if issubclass(defaultType, SerializableType):
                newValue = defaultType.deserialize(newValue, c_badTypeHandling=badTypeHandling, c_variableTrace=[varName])

            # Handle variables of different types to that which is defined in the python module
            if not isinstance(newValue, defaultType):

                # Handle type rejections
                if badTypeHandling.behaviour == BadTypeBehaviour.REJECT:
                    errMsg = f"Unexpected type for config variable {varName}: Expected " \
                            + f"{defaultType.__name__}, received {type(newValue).__name__}"
                    if badTypeHandling.rejectType == ErrorHandling.RAISE:
                        raise TypeError(errMsg)
                    elif badTypeHandling.behaviour == ErrorHandling.LOG:
                        log(f"[WARNING] {errMsg}")

                # Handle type casts
                elif badTypeHandling.behaviour == BadTypeBehaviour.CAST:
                    if isinstance(defaultType, type):
                        try:
                            # Attempt casts for incorrect types - useful for things like ints instead of floats.
                            # TODO: Ignoring a warning here because we intentionally don't know the type or therefore the init signature
                            # In the future I will type this with a protocol before trying the instantiation
                            newValue = defaultType(newValue) # type: ignore[reportGeneralTypeIssues]
                        except Exception as e:
                            if badTypeHandling.keepFailedCast:
                                # Nothing to do if keeping failed variable casts, except log if configured to
                                if badTypeHandling.logTypeKeeping:
                                    log(f"[WARNING] Keeping original value for mistype variable {varName}, following failed " \
                                        + f"cast. Expected {defaultType.__name__}, received {type(newValue).__name__}," \
                                        + f" cast exception: {formatException(e, badTypeHandling.includeExceptionTrace)}")
                            # If configured to reject failed casts
                            else:
                                errMsg = f"Casting failed for unexpected type for config variable {varName}: Expected " \
                                        + f"{defaultType.__name__}, received {type(newValue).__name__}. " \
                                        + f"Cast exception: {formatException(e, badTypeHandling.includeExceptionTrace)}"
                                if badTypeHandling.rejectType == ErrorHandling.RAISE:
                                    raise TypeError(errMsg)
                                elif badTypeHandling.rejectType == ErrorHandling.LOG:
                                    log(f"[WARNING] {errMsg}")

                        # Cast was successful
                        else:
                            if badTypeHandling.logSuccessfulCast and type(newValue).__name__ != defaultType.__name__:
                                log(f"[WARNING] Successfully casted unexpected type for config variable {varName} from type " \
                                    + f"{type(newValue).__name__} to {defaultType.__name__}")
                    else:
                        if badTypeHandling.keepFailedCast:
                            # Nothing to do if keeping failed variable casts, except log if configured to
                            if badTypeHandling.logTypeKeeping:
                                log(f"[WARNING] Keeping original value for mistype variable {varName}, cast not attempted. " \
                                    + f"Cannot instance typing type hint {defaultType!s}. Received {type(newValue).__name__}")
                        # If configured to reject failed casts
                        else:
                            errMsg = f"Cast not attempted for unexpected type for config variable {varName}: " \
                                    + f"Cannot instance typing type hint {defaultType!s}. Received {type(newValue).__name__}"
                            if badTypeHandling.rejectType == ErrorHandling.RAISE:
                                raise TypeError(errMsg)
                            elif badTypeHandling.rejectType == ErrorHandling.LOG:
                                log(f"[WARNING] {errMsg}")


                # Handle type keeping
                elif badTypeHandling.behaviour == BadTypeBehaviour.KEEP:
                    # Nothing to do if keeping mismatched variables, except log if configured to
                    if badTypeHandling.logTypeKeeping:
                        log(f"[WARNING] Keeping original value for mistype variable {varName}. Expected " \
                            + f"{defaultType.__name__}, received {type(newValue).__name__}")

            # Variable value received successfully, inject into python module
            setattr(cfgModule, varName, newValue)

    # No errors encountered
    log("Config successfully loaded: " + cfgFile)
