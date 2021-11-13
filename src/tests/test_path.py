from typing import Tuple, Union
import pytest
from carica.models import SerializablePath
from os.path import join
from os import sep


@pytest.mark.parametrize(("testPath", "possibleData"),
                            [
                                (SerializablePath(join("test", "relative", "path", "to file.toml")),
                                    (
                                        "test/relative/path/to file.toml",
                                        "test\\relative\\path\\to file.toml"
                                    )),
                                (SerializablePath(join(f"C:", sep, "test", "windows", "file path", "like_this.toml")),
                                    (
                                        "C:\\test\\windows\\file path\\like_this.toml",
                                        "C:/test/windows/file path/like_this.toml"
                                    )),

                                (SerializablePath("test", "relative file path", "by-segments.txt"),
                                    (
                                        "test/relative file path/by-segments.txt",
                                        "test\\relative file path\\by-segments.txt"
                                    )),
                                (SerializablePath("D:", sep, "test", "windows file path", "by segments.mp3"),
                                    (
                                        "D:\\test\\windows file path\\by segments.mp3",
                                        "D:/test/windows file path/by segments.mp3"
                                    )),
                            ])
def test_path_serialize_hasCorrectContents(testPath: SerializablePath, possibleData: Tuple[str]):
    serialized = testPath.serialize()
    assert serialized in possibleData


@pytest.mark.parametrize(("testData", "expectedPath"),
                            [
                                (
                                    "test/relative/path/to file.toml",
                                    SerializablePath(join("test", "relative", "path", "to file.toml"))
                                ),
                                (
                                    "test\\relative\\path\\to file.toml",
                                    SerializablePath(join("test", "relative", "path", "to file.toml"))
                                ),
                                (
                                    "C:\\test\\windows\\file path\\like_this.toml",
                                    SerializablePath(join("C:", sep, "test", "windows", "file path", "like_this.toml"))
                                ),
                                (
                                    "test/relative file path/by-segments.txt",
                                    SerializablePath("test", "relative file path", "by-segments.txt")
                                ),
                                (
                                    "test\\relative file path\\by-segments.txt",
                                    SerializablePath("test", "relative file path", "by-segments.txt")
                                ),
                                (
                                    "D:\\test\\windows file path\\by segments.mp3",
                                    SerializablePath("D:", sep, "test", "windows file path", "by segments.mp3")
                                )
                            ])
def test_path_deserialize_hasCorrectContents(testData: str, expectedPath: SerializablePath):
    deserialized = SerializablePath.deserialize(testData)
    assert deserialized.serialize() == expectedPath.serialize()


@pytest.mark.parametrize(("basePath", "newPaths", "expectedPath"),
                            [
                                (
                                    SerializablePath(join("some relative", "folder")),
                                    (
                                        SerializablePath("another folder"),
                                    ),
                                    SerializablePath(join("some relative", "folder", "another folder"))
                                ),
                                (
                                    SerializablePath(join("some relative", "folder")),
                                    (
                                        SerializablePath("another folder"),
                                        SerializablePath("then a file.txt")
                                    ),
                                    SerializablePath(join("some relative", "folder", "another folder", "then a file.txt"))
                                ),
                                (
                                    SerializablePath("some relative/folder"),
                                    (
                                        "x",
                                        SerializablePath("y")
                                    ),
                                    SerializablePath(join("some relative", "folder", "x", "y"))
                                ),
                                (
                                    SerializablePath("some relative/folder"),
                                    (
                                        "x",
                                        SerializablePath("y", "z.txt")
                                    ),
                                    SerializablePath(join("some relative", "folder", "x", "y", "z.txt"))
                                ),
                                (
                                    SerializablePath("some relative/folder"),
                                    (
                                        "x",
                                        SerializablePath("y"),
                                        "z.txt"
                                    ),
                                    SerializablePath(join("some relative", "folder", "x", "y", "z.txt"))
                                ),
                            ])
def test_path_addition_isCorrect(basePath: SerializablePath, newPaths: Tuple[Union[SerializablePath, str]],
                                    expectedPath: SerializablePath):
    for path in newPaths:
        basePath += path
    assert basePath == expectedPath
    