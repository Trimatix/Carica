from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Union

PrimativeType = Union[int, float, str, bool, List["PrimativeType"], Dict["PrimativeType", "PrimativeType"], Set["PrimativeType"]] # type: ignore


class ISerializable(ABC):
    """An object which can be represented entirely by a dictionary of primitives, created with the toDict method.
    This object can then be recreated perfectly using the fromDict method.
    """
    
    @abstractmethod
    def serialize(self, **kwargs) -> PrimativeType:
        """Serialize this object into primative types (likely a dictionary, e.g JSON), to be recreated completely.

        :return: A primative (likely a dictionary) containing all information needed to recreate this object
        :rtype: PrimativeType
        """
        raise NotImplementedError()


    @abstractmethod
    @classmethod
    def deserialize(cls, data: PrimativeType, **kwargs) -> ISerializable:
        """Recreate a serialized ISerializable object

        :param PrimativeType data: A primative (likely a dictionary) containing all information needed to recreate the serialized object
        :return: A new object as specified by data
        :rtype: ISerializable
        """
        raise NotImplementedError()
