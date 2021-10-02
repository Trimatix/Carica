# myType is not a variable
# so this multiline comment shouldn't be detected
class MyType:
    pass

# this multiline comment
# doesn't belong to myCustomType

myCustomType = MyType()