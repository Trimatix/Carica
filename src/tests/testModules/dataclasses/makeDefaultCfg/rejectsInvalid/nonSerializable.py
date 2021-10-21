from carica.models import SerializableDataClass
from dataclasses import dataclass

class MyNonSerializableType:
    pass

@dataclass
class MyNonSerializableDataClass(SerializableDataClass):
    invalidField: MyNonSerializableType

nonSerializableVariable = MyNonSerializableDataClass(
    invalidField = MyNonSerializableType()
)
