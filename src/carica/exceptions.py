from typing import Any, Optional, List, Union


class KeyTracedException(Exception):
    """Base exception type for exceptions which occur when scanning potentially recursive types.
    
    :ivar o: The erroneous object
    :vartype o: Any
    :ivar depth: If the error occured when studying an object inside of an iterable or mapping, this represents the number
                of objects deep where the erroneous object was located. E.g in [[x]], x is 2 layers deep
    :vartype depth: Optional[int]
    :ivar path:  If the error occured when studying an object inside of an iterable or mapping, this path should trace
                the keys/indices accessed to reach the object
    :vartype path: Optional[List[Union[str, int]]]
    :ivar extra: Any extra details which may be useful for debugging or locating the erroneous object
    :vartype extra: str
    """
    
    def __init__(self, o: Any, depth: Optional[int] = None, path: Optional[List[Union[str, int]]] = None,
                        extra: Optional[str] = None) -> None:
        """
        :param o: The erroneous object
        :type o: Any
        :param depth: If the error occured when studying an object inside of an iterable or mapping, this represents the number
                of objects deep where the erroneous object was located. E.g in [[x]], x is 2 layers deep
        :type depth: Optional[int]
        :param path:  If the error occured when studying an object inside of an iterable or mapping, this path should trace
                    the keys/indices accessed to reach the object (Default None)
        :type path: Optional[List[Union[str, int]]]
        :param extra: Any extra details which may be useful for debugging or locating the erroneous object (Default None)
        :type extra: str
        """
        self.o = o
        if depth is None and path is not None:
            depth = len(path)
        self.depth = depth
        self.path = path
        self.extra = extra
        super().__init__()


    def formatPathInfo(self) -> str:
        """Format the exception's depth, path and extra info into a single string, if they exist.

        :return: A nicely formatted string with the depth, path and extra info of the exception, if they exist
        :rtype: str
        """
        info = ""
        if self.depth:
            info += f"at depth {self.depth}"
        if self.path:
            info += f"{' ' if self.depth else ''}({'->'.join(str(i) for i in self.path)})"
        if self.extra:
            info += f"{' ' if self.depth or self.path else ''}({self.extra})"
        
        return info


    def __str__(self) -> str:
        return f"object '{repr(self.o)}' {self.formatPathInfo()}"


class NonSerializableObject(KeyTracedException):
    """Exception to be raised when attempting to serialize an object of a non-serializable type.
    """
    pass


class NonStringMappingKey(KeyTracedException):
    """Exception to be raised when attempting to serialize a mapping (dict) which has a key that is not a str.
    """
    pass


class MultiTypeList(KeyTracedException):
    """Exception to be raised when attempting to serialize a list containing both tables (dicts) and non-table types.
    """
    def __str__(self) -> str:
        return f"List contains both dicts and non-dict types {self.formatPathInfo()}"
