from carica.models import SerializableDataClass
from carica.typeChecking import TypeOverride
from dataclasses import dataclass, field
from typing import List, cast

@dataclass
class MySerializableDataClass(SerializableDataClass):
    listNotIntVar: int = field(default_factory=TypeOverride(List[str], lambda: 1))

mySerializableField = MySerializableDataClass(
    listNotIntVar = cast(int, [])
)