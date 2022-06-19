from carica.models import SerializableDataClass
from carica.typeChecking import TypeOverride
from dataclasses import dataclass
from typing import cast

@dataclass
class MySerializableDataClass(SerializableDataClass):
    intVar: int = TypeOverride(str, cast(int, "1"))

mySerializableField = MySerializableDataClass(
    intVar = cast(int, "1")
)