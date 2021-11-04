from typing import Any, Dict, List, Union, cast
from tomlkit.container import Container as TKContainer
from tomlkit.items import AoT

INCOMPATIBLE_TOML_TYPES = (TKContainer, AoT)

def convertIncompatibleTomlTypes(doc: Union[TKContainer, AoT]) -> Union[List[Any], Dict[str, Any]]:
    """Recursively converts tomlkit tables/lists of tables into dictionaries/lists of dictionaries

    :param doc: The item to convert
    :type doc: Union[TKContainer, AoT]
    :return: doc recursively converted to python types instead of TOMLKit Containers/AoTs
    """
    if isinstance(doc, TKContainer):
        # Not sure why mypy doesn't pick up on Container inheriting from dict
        return {k: convertIncompatibleTomlTypes(v) for k, v in  cast(dict, doc).items()}
    elif isinstance(doc, AoT):
        return [convertIncompatibleTomlTypes(v) for v in doc]
    else:
        return doc
