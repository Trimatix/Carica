class MySerializableClass:
    def __init__(self, myField) -> None:
        self.myField = myField


    def serialize(self, **kwargs):
        return {"myField": self.myField}


    @classmethod
    def deserialize(cls, data, **kwargs):
        return MySerializableClass(data["myField"])

    
    def __eq__(self, o: object) -> bool:
        return isinstance(o, MySerializableClass) and o.myField == self.myField


    def __str__(self):
        return f"<myField={self.myField}>"


mySerializableVar = MySerializableClass("hello")