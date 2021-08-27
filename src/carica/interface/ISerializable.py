from __future__ import annotations
from abc import ABC, abstractmethod


class ISerializable(ABC):
    """An object which can be represented entirely by a dictionary of primitives, created with the toDict method.
    This object can then be recreated perfectly using the fromDict method.
    """
    
    @abstractmethod
    def toDict(self, **kwargs) -> dict:
        """Serialize this object into dictionary format, to be recreated completely.

        :return: A dictionary containing all information needed to recreate this object
        :rtype: dict
        """
        raise NotImplementedError()


    @abstractmethod
    @classmethod
    def fromDict(cls, data: dict, **kwargs) -> ISerializable:
        """Recreate a dictionary-serialized ISerializable object 

        :param dict data: A dictionary containing all information needed to recreate the serialized object
        :return: A new object as specified by the attributes in data
        :rtype: ISerializable
        """
        raise NotImplementedError()
