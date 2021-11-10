from carica.models import SerializableDataClass
from dataclasses import dataclass
from typing import List, Union, Dict

@dataclass
class TestClass(SerializableDataClass):
    intVar: int
    stringVar: str
    floatVar: float
    listVar: List[Union[str, int]]
    dictVar: Dict[str, str]
    aotVar: List[Dict[str, str]]

testVar = TestClass(
    intVar = 1,
    stringVar = "hello",
    floatVar = 1.0,
    listVar = [3, "hello"],
    dictVar = {
        "myField": "value"
    },
    aotVar = [
        {
            "myField": "value"
        },
        {
            "myField": "value"
        }
    ]
)