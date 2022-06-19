from typing import Dict, TypeVar, Type
from carica.interface.Serializable import ISerializable, PrimativeType
from datetime import timedelta

TSelf = TypeVar("TSelf", bound="SerializableTimedelta")

class SerializableTimedelta(ISerializable, timedelta):
    """A serializable version of `datetime.timedelta`. For `datetime.datetime`, no extra handling is needed,
    as datetime is considered a primitive type by TOML.
    """
    @classmethod
    def fromTimedelta(cls, td: timedelta):
        """Create a new `SerializableTimedelta` from an existing `datetime.timedelta`.

        :param timedelta td: The timedelta to duplicate
        """
        return cls(days=td.days, seconds=td.seconds, microseconds=td.microseconds)


    def serialize(self, **kwargs) -> Dict[str, int]:
        """Serialize this timedelta into the simplest representation possible - using the largest amounts of the largest
        units that will fit into this timedelta.

        :return: A dictionary containing all units, each possibly zero, to represent this timedelta.
        :rtype: Dict[str, int]
        """
        data = {}

        data["weeks"] = 0 if self.days < 7 else self.days // 7
        data["days"] = self.days - data["weeks"] * 7

        data["hours"] = 0 if self.seconds < 3600 else self.seconds // 3600
        seconds = self.seconds - data["hours"] * 3600
        data["minutes"] = 0 if seconds < 60 else seconds // 60
        data["seconds"] = seconds - data["minutes"] * 60
        
        data["milliseconds"] = 0 if self.microseconds < 1000 else self.microseconds // 1000
        data["microseconds"] = self.microseconds - data["milliseconds"] * 1000
            
        return data


    @classmethod
    def deserialize(cls: Type[TSelf], data: PrimativeType, **kwargs) -> TSelf:
        if not isinstance(data, dict):
            raise TypeError(f"Invalid serialized {cls.__name__}: {data}")
        return cls(**data)
