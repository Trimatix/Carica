class MySerializableType:
    def __init__(self, myField) -> None:
        self.myField = myField


    def serialize(self, **kwargs):
        return {"myField": self.myField}

    @classmethod
    def deserialize(cls, data, **kwargs):
        return MySerializableType(**data)


class MyNonSerializableType:
    pass


class MyInvalidSerializableType:
    def serialize(self, **kwargs):
        return {"myField": MyNonSerializableType()}


    @classmethod
    def deserialize(cls, data, **kwargs):
        return MySerializableType(**data)
