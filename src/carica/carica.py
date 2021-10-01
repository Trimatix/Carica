from types import ModuleType
import tomlkit
import os
from typing import Any, Dict, List, Union, Iterable, Mapping
import tokenize
from carica.interface import SerializableType, PrimativeType
from carica.typeChecking import objectIsShallowPrimative
from carica import exceptions
from dataclasses import dataclass

CFG_FILE_EXT = ".toml"
DISALLOWED_TOKEN_TYPES = {tokenize.INDENT}
DISALLOWED_TOKEN_TYPE_VALUES = {tokenize.NAME: {"from", "import"}}
LINE_DELIMITER_TOKEN_TYPES = {tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER}


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
    return line[0].type == tokenize.NAME and any(t.type == tokenize.OP and t.string == "=" for t in line)


@dataclass
class ConfigVariable:
    name: str
    value: Any
    inlineComments: List[str]
    preComments: List[str]


    def hasInline(self):
        return self.inlineComments != []


    def hasPre(self):
        return self.preComments != []


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
    with tokenize.open(module.__file__) as f:
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
                                variableValue = getattr(module, variableName)
                                moduleVariables[variableName] = ConfigVariable(variableName, variableValue, [], [])

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
                            moduleVariables[variableName] = ConfigVariable(variableName, variableValue, [], [])

                        # Record the found inline comment
                        moduleVariables[variableName].inlineComments.append(token.string.lstrip("# "))
                
                # Is it a comment line?
                else:
                    # Add the comment text to the preceeding comments queue
                    commentsQueue.append(token.string.lstrip("# "))
                    currentLine.append(token)

            # No processing of this token to be performed, record it and move onto the next one in the line
            else:
                currentLine.append(token)
        
    return moduleVariables


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
    defaults = {k: getattr(cfgModule, k) for k in _partialModuleVariables(cfgModule) if k in cfgModule.__dict__}
    
    # Serialize serializable objects and reject non-serializable/non-primative variables
    for varName, varValue in defaults.items():
        defaults[varName] = _serialize(varValue, [varName], serializerKwargs=serializerKwargs)

    # Dump to toml and write to file
    with open(cfgPath, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(defaults).lstrip("\n"))

    # Print and return path to new file
    print("Created " + cfgPath)
    return cfgPath


# TODO: This code has been copied in pretty much 1-1 from bountybot, refactor it and test it
def loadCfg(cfgModule: ModuleType, cfgFile: str, raiseOnUnknownVar: bool = True):
    """Load the values from a specified config file into attributes of the python cfg module.
    All config attributes are optional, but if a mapping is given, all desired values must be set.

    :param ModuleType cfgModule: Module to load variable values into
    :param str cfgFile: Path to the file to load. Can be relative or absolute
    :param bool raiseOnUnknownVar: Whether to raise an exception or simply print a warning when attempting to load a variable
                                    from cfgFile which is not named in cfgModule (Default True)
    :raise ValueError: When cfgFile is of an unsupported format
    """
    # Ensure the given config is toml
    if not cfgFile.endswith(CFG_FILE_EXT):
        raise ValueError("config files must be TOML")

    # Load from toml to dictionary
    with open(cfgFile, "r", encoding="utf-8") as f:
        config = toml.loads(f.read())

    # Read default config values
    defaults = {k: getattr(cfgModule, k) for k in _partialModuleVariables(cfgModule) if k in cfgModule.__dict__}

    # Assign config values to cfg attributes
    for varname in config:
        # Validate attribute names
        if varname not in defaults:
            if raiseOnUnknownVar:
                raise NameError("Unrecognised config variable name: " + varname)
            else:
                print("[WARNING] Ignoring unrecognised config variable name: " + varname)

        else:
            # Get default value for variable
            default = defaults[varname]
            newvalue = config[varname]

            # deserialize serializable variables
            if isinstance(default, SerializableType):
                newvalue = type(default).deserialize(newvalue)

            # Ensure new value is of the correct type
            if type(config[varname]) != type(default):
                try:
                    # Attempt casts for incorrect types - useful for things like ints instead of floats.
                    config[varname] = type(default)(config[varname])
                    print("[WARNING] Casting config variable " + varname + " from " + type(config[varname]).__name__ \
                            + " to " + type(default).__name__)
                except Exception:
                    # Where a variable is of the wrong type and cannot be casted, raise an exception.
                    raise TypeError("Unexpected type for config variable " + varname + ": Expected " \
                                    + type(default).__name__ + ", received " + type(config[varname]).__name__)

            setattr(cfgModule, varname, config[varname])

    # No errors encountered
    print("Config successfully loaded: " + cfgFile)
