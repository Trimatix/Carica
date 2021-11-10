from carica.models import SerializableDataClass
from dataclasses import dataclass
from typing import Dict

@dataclass
class MyNonSerializableDataClass(SerializableDataClass):
    invalidField: Dict[int, str]

invalidVar = MyNonSerializableDataClass(
    invalidField = {
        1: "value"
    }
)
