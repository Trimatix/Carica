from types import ModuleType
import toml
import os
from typing import Any, Dict, List, Union, Iterable, Mapping
import tokenize
from carica.interface import SerializableType, PrimativeType
from carica.typeChecking import objectIsShallowPrimative
from carica import exceptions

CFG_FILE_EXT = ".toml"
DISALLOWED_TOKEN_TYPES = {tokenize.INDENT}
DISALLOWED_TOKEN_TYPE_VALUES = {tokenize.NAME: {"from", "import"}}
LINE_DELIMITER_TOKEN_TYPES = {tokenize.NL, tokenize.NEWLINE}


def tokenDisallowed(token: tokenize.TokenInfo) -> bool:
    """Decide whether or not a token can be present in avariable assignment line.
    The return value is the inverse of what you would expect: True if the token can NOT be part of a variable assignment line.

    :param tokenize.TokenInfo token: The token to check
    :return: True if the token is an ILLEGAL part of a variable assignment, False if the token is LEGAL.
    :rtype: bool
    """
    return token.type in DISALLOWED_TOKEN_TYPES or \
        (token.type in DISALLOWED_TOKEN_TYPE_VALUES and token.string in DISALLOWED_TOKEN_TYPE_VALUES[token.type])


def _partialModuleVarNames(module: ModuleType) -> List[str]:
    """Estimate a list of variable names defined in module.
    Attempts to ignore other name types, such as functions, classes and imports.
    Names cannot be indented, and multiple assignment is not supported - variable declarations must be on their own lines.

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
    :return: An estimated list of variable names defined in module. See above for details and limitations.
    :rtype: List[str]
    """
    with tokenize.open(module.__file__) as f:
        tokens = tokenize.generate_tokens(f.readline)
        moduleVarNames: List[str] = []
        currentLine: List[tokenize.TokenInfo] = []
        for token in tokens:
            if currentLine == [] and tokenDisallowed(token):
                continue
            elif token.type in LINE_DELIMITER_TOKEN_TYPES:
                if currentLine:
                    if currentLine[0].type == tokenize.NAME and any(t[0] == tokenize.OP and t[1] == "=" for t in currentLine):
                        moduleVarNames.append(currentLine[0][1])
                    currentLine = []
            else:
                currentLine.append(token)
        
    return moduleVarNames


def _serialize(o: Any, path: List[Union[str, int]], depthLimit=20, serializerKwargs={}) -> PrimativeType:
    """Internal recursive method to serialize any serializable object, or throw exceptions with useful key trace info
    """
    # Check recursion depth
    if len(path) > depthLimit:
        raise RecursionError()

    # o is directly serializable, serialize it and return that
    if isinstance(o, SerializableType):
        return _serialize(o.serialize(**serializerKwargs), path + ["[serialize]"], depthLimit=depthLimit,
                            serializerKwargs=serializerKwargs)

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

    # o is a mapping, serialize each value
    elif isinstance(o, Mapping):
        serializedDict: Dict[str, PrimativeType] = {}
        for k, v in o.items():
            # ensure keys are str
            if not isinstance(k, str):
                raise exceptions.NonStringMappingKey(k, len(path)-1, path)

            serializedDict[k] = _serialize(v, path + [k], depthLimit=depthLimit, serializerKwargs=serializerKwargs)
        return serializedDict

    # o is just a normal primative, return it as is
    elif objectIsShallowPrimative(o):
        return o

    # unable to match serializing method, exception time
    raise exceptions.NonSerializableObject(o, len(path)-1, path)


def makeDefaultCfg(cfgModule: ModuleType, fileName: str = "defaultCfg" + CFG_FILE_EXT, **serializerKwargs) -> str:
    """Create a config file containing all configurable variables with their default values.
    The name of the generated file may optionally be specified.

    fileName may also be a path, either relative or absolute. If missing directories are specified
    in fileName, they will be created.

    If fileName already exists, then the generated file will be renamed with an incrementing number extension.

    :param ModuleType cfgModule: Module to convert to toml
    :param str fileName: Path to the file to generate (Default "defaultCfg.toml")
    :return: path to the generated config file
    :rtype: str
    :raise ValueError: If fileName does not end in CFG_FILE_EXT
    """
    # Ensure fileName is toml
    if not fileName.endswith(CFG_FILE_EXT):
        print(fileName)
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
    defaults = {k: getattr(cfgModule, k) for k in _partialModuleVarNames(cfgModule) if k in cfgModule.__dict__}
    
    # Serialize serializable objects and reject non-serializable/non-primative variables
    for varName, varValue in defaults.items():
        defaults[varName] = _serialize(varValue, [varName], serializerKwargs=serializerKwargs)

    # Dump to toml and write to file
    with open(cfgPath, "w", encoding="utf-8") as f:
        f.write(toml.dumps(defaults))

    # Print and return path to new file
    print("Created " + cfgPath)
    return cfgPath