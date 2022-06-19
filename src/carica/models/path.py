from typing import Type, TypeVar
from carica.interface import ISerializable, PrimativeType
from pathlib import Path, WindowsPath, PosixPath
import os

TSelf = TypeVar("TSelf", bound="SerializablePath")

class SerializablePath(ISerializable, Path):
    """A serializable path intended to be treated as a string.
    This class serializes into a usable string.

    This class directly copies the instancing logic of pathlib.Path in order to achieve subclassing.
    For more details, see the implementation of pathlib.Path, and this stackoverflow thread (which has not been followed):
    https://stackoverflow.com/questions/29850801/subclass-pathlib-path-fails
    """

    def __new__(cls, *args, **kwargs) -> "SerializablePath":
        if cls is SerializablePath:
            cls = SerializableWindowsPath if os.name == 'nt' else SerializablePosixPath
        # ignoring a warning here on missing method _from_parts
        # the OS-specific serializable path subclasses still transitively extend Path, so _from_parts is guaranteed
        self = cls._from_parts(args, init=False) # type: ignore[reportGeneralTypeIssues]
        if not self._flavour.is_supported:
            raise NotImplementedError("cannot instantiate %r on your system"
                                      % (cls.__name__,))
        self._init()
        return self


    def serialize(self, **kwargs) -> str:
        """Return this path as a string.

        :return: The path as a string
        :rtype: str
        """
        return str(self)


    @classmethod
    def deserialize(cls: Type[TSelf], data: PrimativeType, **kwargs) -> TSelf:
        """Form a SerializablePath from a string. Separation of the path into parts is handled by pathlib.Path logic.

        :param str data: The path to deserialize, as an os.sep-separated string of path parts.
        :return: A new SerializablePath representing data
        :rtype: SerializablePath
        """
        if not isinstance(data, str):
            raise TypeError(f"Invalid type for parameter data. Expected str, received {type(data).__name__}")
        return cls(data)


    def __add__(self: TSelf, other: object) -> TSelf:
        """Concatenate two paths into a new SerializablePath. Neither this nor other are modified.

        :param other: The path to appear on the right-hand side of the new path
        :type other: Union[str, Path, SerializablePath]
        :return: A new SerializablePath containing this path followed by other, separated with os.sep as necessary
        """
        if isinstance(other, str):
            return type(self)(*(self.parts + (other,)))
        elif isinstance(other, Path):
            return type(self)(*(self.parts + other.parts))
        else:
            raise TypeError(f"Incompatible types: {type(self).__name__} and {type(other).__name__}")


class SerializableWindowsPath(SerializablePath, WindowsPath):
    pass

class SerializablePosixPath(SerializablePath, PosixPath):
    pass
