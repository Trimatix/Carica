from __future__ import annotations
from typing import Dict, List, Set, Union, Protocol, runtime_checkable

PrimativeType = Union[int, float, str, bool, List["PrimativeType"], Dict["PrimativeType", "PrimativeType"], Set["PrimativeType"]] # type: ignore


@runtime_checkable
class ISerializable(Protocol):
    """An object which can be represented entirely by a dictionary of primitives, created with the toDict method.
    This object can then be recreated perfectly using the fromDict method.
    """
    
    def serialize(self, **kwargs) -> PrimativeType:
        """Serialize this object into primative types (likely a dictionary, e.g JSON), to be recreated completely.

        :return: A primative (likely a dictionary) containing all information needed to recreate this object
        :rtype: PrimativeType
        """
        ...


    @classmethod
    def deserialize(cls, data: PrimativeType, **kwargs) -> ISerializable:
        """Recreate a serialized ISerializable object

        :param PrimativeType data: A primative (likely a dictionary) containing all information needed to recreate the serialized object
        :return: A new object as specified by data
        :rtype: ISerializable
        """
        ...
