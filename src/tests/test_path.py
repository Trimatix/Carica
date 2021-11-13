from typing import Tuple
import pytest
from carica.models import SerializablePath


@pytest.mark.parametrize(("testPath", "possibleData"),
                            [
                                (SerializablePath("test/relative/path/to file.toml"),
                                    (
                                        "test/relative/path/to file.toml",
                                        "test\\relative\\path\\to file.toml"
                                    )),
                                ("C:\\test\\windows\\file path\\like_this.toml",
                                    (
                                        "C:\\test\\windows\\file path\\like_this.toml",
                                    )),
                            ])
def test_path_serialize_hasCorrectContents(testPath: SerializablePath, possibleData: Tuple[str]):
    serialized = testPath.serialize()
    return
