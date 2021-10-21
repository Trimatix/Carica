from carica.models import SerializableDataClass
from dataclasses import dataclass
from typing import List, Union

@dataclass
class MyNonSerializableDataClass(SerializableDataClass):
    invalidField: List[Union[int, dict]]

mySerializableField = MyNonSerializableDataClass(
    invalidField = [1, {"key": "value"}]
)
