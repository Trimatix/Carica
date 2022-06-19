from typing import cast
from carica.models import SerializableDataClass
from carica.typeChecking import TypeOverride
from dataclasses import dataclass

class MySerializableClass:
    def __init__(self, myField) -> None:
        self.myField = myField


    def serialize(self, **kwargs):
        return {"myField": self.myField}


    @classmethod
    def deserialize(cls, data, **kwargs):
        return MySerializableClass(data["myField"])


@dataclass
class MySerializableDataClass(SerializableDataClass):
    myField: int = TypeOverride(MySerializableClass, cast(int, MySerializableClass))

testVar = MySerializableDataClass(
    myField = cast(int, MySerializableClass("test"))
)
