from carica.interface import ISerializable, PrimativeType
from pathlib import Path

class SerializablePath(ISerializable, Path):
    """A serializable path intended to be treated as a string.
    This class serializes into a usable string.
    """

    def serialize(self, **kwargs) -> str:
        """Return this path as a string.

        :return: The path as a string
        :rtype: strs
        """
        return str(self)


    @classmethod
    def deserialize(cls, data: PrimativeType, **kwargs) -> "SerializablePath":
        """Form a SerializablePath from a string. Separation of the path into parts is handled by pathlib.Path logic.

        :param str data: The path to deserialize, as an os.sep-separated string of path parts.
        :return: A new SerializablePath representing data
        :rtype: SerializablePath
        """
        if not isinstance(data, str):
            raise TypeError(f"Invalid type for parameter data. Expected str, received {type(data).__name__}")
        return SerializablePath(data)


    def __add__(self, other: object) -> "SerializablePath":
        """Concatenate two paths into a new SerializablePath. Neither this nor other are modified.

        :param other: The path to appear on the right-hand side of the new path
        :type other: Union[str, Path, SerializablePath]
        :return: A new SerializablePath containing this path followed by other, separated with os.sep as necessary
        """
        if isinstance(other, str):
            return SerializablePath(*(self.parts + (other,)))
        elif isinstance(other, Path):
            return SerializablePath(*(self.parts + other.parts))
        else:
            raise TypeError(f"Incompatible types: {type(self).__name__} and {type(other).__name__}")
