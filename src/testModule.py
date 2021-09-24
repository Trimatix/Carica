from testClasses import *

stringVar = "test string"
validSerializableVar = MySerializableType("my value")
# invalidSerializableVar = MyNonSerializableType()
# anotherInvalidSerializableVar = MyInvalidSerializableType()
validDictVar = {"primitiveValue": 1, "dictValue": {"primative value with spaces": "testing", "serializableValue": validSerializableVar}}
# invalidDictVar = {"1": 2, "invalidSerializableValue": MyNonSerializableType()}
validList1 = [3, 4]
validListVar = [1, [validDictVar, validDictVar]]
# invalidListVar = [2, {"1": 2, "invalidSerializableValue": MyNonSerializableType()}]
# anotherInvalidListVar = [2, {"1": 2, "validSerializableVar": validSerializableVar}]
