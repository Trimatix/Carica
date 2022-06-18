from typing import Dict
from carica.typeChecking import TypeOverride

class MySerializableClass:
    def __init__(self, myField) -> None:
        self.myField = myField


    def serialize(self, **kwargs):
        return {"myField": self.myField}


    @classmethod
    def deserialize(cls, data, **kwargs):
        return MySerializableClass(data["myField"])


mySerializableVar = TypeOverride(dict, MySerializableClass("hello"))