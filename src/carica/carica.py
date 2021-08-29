from types import ModuleType
import toml
import os
from typing import Dict, Any, List, Tuple, cast
import tokenize

CFG_FILE_EXT = ".toml"


def _partialModuleVarNames(module: ModuleType) -> List[str]:
    """Estimate
    """
    with tokenize.open(module.__file__) as f:
        tokens = tokenize.generate_tokens(f.readline)
        moduleVarNames: List[str] = []
        currentLine: List[tuple] = []
        for token in tokens:
            if currentLine == [] and token[0] == tokenize.INDENT:
                continue
            elif currentLine == [] and token[0] == tokenize.NAME and token[1] in ("from", "import"):
                continue
            elif token[0] in (tokenize.NEWLINE, tokenize.NL):
                if currentLine[0][0] == tokenize.NAME and any(t[0] == tokenize.OP and t[1] == "=" for t in currentLine):
                    moduleVarNames.append(currentLine[0][1])
                currentLine = []
            else:
                currentLine.append(token)
        
    return moduleVarNames


def makeDefaultCfg(cfgModule: ModuleType, fileName: str = "defaultCfg" + CFG_FILE_EXT) -> str:
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
    defaults = {varname: varvalue for varname, varvalue in vars(cfgModule).items() if varname not in ignoredVarNames}
    # Read default emoji values
    for varname in emojiVars:
        
        defaults["defaultEmojis"][varname] = cast(UninitializedBasedEmoji, cfgModule.defaultEmojis[varname]).value
    # Read default emoji list values
    for varname in emojiListVars:
        working = []
        for item in defaults["defaultEmojis"][varname]:
            working.append(item.value)

        defaults["defaultEmojis"][varname] = working

    # Dump to toml and write to file
    with open(cfgPath, "w", encoding="utf-8") as f:
        f.write(toml.dumps(defaults))

    # Print and return path to new file
    print("Created " + cfgPath)
    return cfgPath