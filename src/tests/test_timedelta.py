from datetime import timedelta
from typing import Callable, Dict
import pytest
from carica.models import SerializableTimedelta
from random import randint
import random

RANDOM_SEED = 2128348248

random.seed(RANDOM_SEED)


key_tdGetters: Dict[str, Callable[[timedelta], int]] = {
    "weeks": lambda td: 0 if td.days < 7 else td.days // 7,
    "days": lambda td: td.days - key_tdGetters["weeks"](td) * 7,
    "hours": lambda td: 0 if td.seconds < 3600 else td.seconds // 3600,
    "minutes": lambda td: 0 if (td.seconds % 3600) < 60 else (td.seconds % 3600) // 60,
    "seconds": lambda td: td.seconds - (key_tdGetters["hours"](td) * 3600) - (key_tdGetters["minutes"](td) * 60),
    "milliseconds": lambda td: 0 if td.microseconds < 1000 else td.microseconds // 1000,
    "microseconds": lambda td: td.microseconds - key_tdGetters["milliseconds"](td) * 1000
}


def distributeSerializedData(data: Dict[str, int]) -> Dict[str, int]:
    """This will flatten out all of the values in data, pushing times up to the largest 'bases' they can fit in
    This creates a minimal dict for replacing the same data
    """
    td = timedelta(**data)
    return {k: key_tdGetters[k](td) for k in key_tdGetters}


def randomTestData(mini=1, maxi=1000):
    weeks = randint(mini, maxi)
    days = randint(mini, maxi)
    hours = randint(mini, maxi)
    minutes = randint(mini, maxi)
    seconds = randint(mini, maxi)
    milliseconds = randint(mini, maxi)
    microseconds = randint(mini, maxi)
    td = SerializableTimedelta(
        weeks=weeks,
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        milliseconds=milliseconds,
        microseconds=microseconds
    )
    data = {
        "weeks": weeks,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "milliseconds": milliseconds,
        "microseconds": microseconds
    }
    return td, data


sampleData = [
    (
        # All fields
        SerializableTimedelta(
            weeks=1,
            days=2,
            hours=14,
            minutes=1,
            seconds=532,
            milliseconds=2345,
            microseconds=1
        ),
        {
            "weeks": 1,
            "days": 2,
            "hours": 14,
            "minutes": 1,
            "seconds": 532,
            "milliseconds": 2345,
            "microseconds": 1
        }
    ),
    (
        # No fields
        SerializableTimedelta(),
        {
            "weeks": 0,
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "seconds": 0,
            "milliseconds": 0,
            "microseconds": 0
        }
    ),
    (
        # Minimal fields
        SerializableTimedelta(
            microseconds=1
        ),
        {
            "microseconds": 1
        }
    )
]

numRandomItems = 10

# Add a load of randomly generated test data
sampleData += [randomTestData() for _ in range(numRandomItems)]


@pytest.mark.parametrize(("testTD", "expectedData"), sampleData)
def test_timedelta_serialize_hasCorrectContents(testTD: SerializableTimedelta, expectedData: Dict[str, int]):
    serialized = testTD.serialize()
    expectedData = distributeSerializedData(expectedData)
    for k in key_tdGetters:
        if key_tdGetters[k](testTD) != 0:
            assert k in serialized
            assert k in expectedData
            assert serialized[k] == expectedData[k]
    return True


@pytest.mark.parametrize(("testData", "expectedTD"), [(data, td) for td, data in sampleData])
def test_timedelta_deserialize_hasCorrectContents(testData: str, expectedTD: SerializableTimedelta):
    deserialized = SerializableTimedelta.deserialize(testData)
    assert deserialized == expectedTD
    return True


@pytest.mark.parametrize(("testTD", "expectedTD"), [(timedelta(**data), td) for td, data in sampleData])
def test_timedelta_fromTimedelta_hasCorrectContents(testTD: timedelta, expectedTD: SerializableTimedelta):
    newTD = SerializableTimedelta.fromTimedelta(testTD)
    assert test_timedelta_serialize_hasCorrectContents(newTD, expectedTD.serialize())
    return True
