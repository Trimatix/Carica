from carica.typeChecking import TypeOverride

intVar = TypeOverride(str, 1)
stringVar = "hello"
floatVar = 1.0
listVar = [3, "hello"]
dictVar = {
    "myField": "value"
}
aotVar = [dictVar, dictVar]