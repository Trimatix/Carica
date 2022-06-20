from typing import Dict, List
import pytest
import carica
from carica import typeChecking
import importlib
import os
import shutil
import tomlkit
from tomlkit.items import AbstractTable


TESTS_TEMP_DIR = "testsTemp"


def cleanupTempDir():
    if os.path.isdir(TESTS_TEMP_DIR):
        shutil.rmtree(TESTS_TEMP_DIR)


def setupTempDir():
    cleanupTempDir()
    os.makedirs(TESTS_TEMP_DIR)


@pytest.mark.parametrize(("testModulePath", "testConfigPath"),
                            [
                                ("testModules.dataclasses.loadCfg.loadsCorrectValues.primativeTypes",
                                    "src/tests/testConfigs/dataclasses/loadCfg/loadsCorrectValues/primativeTypes.toml"),
                                ("testModules.dataclasses.loadCfg.loadsCorrectValues.serializableTypes",
                                    "src/tests/testConfigs/dataclasses/loadCfg/loadsCorrectValues/serializableTypes.toml"),
                            ])
def test_dataclasses_loadCfg_loadsCorrectValues(testModulePath, testConfigPath):
    testModule = importlib.import_module(testModulePath)
    with open(testConfigPath, "r") as f:
        testConfigValues = tomlkit.loads(f.read())

    # Make sure at least one field in the config is a SerializableDataClass
    cfgHasDataClass = False
    for varName in testConfigValues:
        if isinstance(getattr(testModule, varName), carica.models.SerializableDataClass):
            cfgHasDataClass = True
            varValue = getattr(testModule, varName)
            # Make sure the test config actually changes something
            assert not varValue == testConfigValues[varName]

    if not cfgHasDataClass:
        raise ValueError("Functionality not tested - no SerializableDataClass detected")

    carica.loadCfg(testModule, testConfigPath)

    # Make sure the config values were loaded in
    for varName in testConfigValues:
        assert carica.carica._serialize(getattr(testModule, varName), [varName]) == testConfigValues[varName]


@pytest.mark.parametrize(("testModulePath", "testConfigPath", "expectedException"),
                            [
                                ("testModules.dataclasses.loadCfg.rejectsInvalid.incorrectTypes_primativeTypes",
                                    "src/tests/testConfigs/dataclasses/loadCfg/rejectsInvalid/incorrectTypes_primativeTypes.toml",
                                    TypeError),
                                ("testModules.dataclasses.loadCfg.rejectsInvalid.incorrectTypes_serializableTypes",
                                    "src/tests/testConfigs/dataclasses/loadCfg/rejectsInvalid/incorrectTypes_serializableTypes.toml",
                                    TypeError)
                            ])
def test_dataclasses_loadCfg_rejectsInvalid(testModulePath, testConfigPath, expectedException):
    testModule = importlib.import_module(testModulePath)

    with pytest.raises(expectedException):
        carica.loadCfg(testModule, testConfigPath)


# All comment tests disabled for now because this functionality is incomplete
@pytest.mark.parametrize(("testModulePath", "expectedOutputPath"),
                            [
                                ("testModules.dataclasses.makeDefaultCfg.hasCorrectContents.primativeTypes",
                                    "src/tests/testConfigs/dataclasses/makeDefaultCfg/hasCorrectContents/primativeTypes.toml"),
                                # ("testModules.dataclasses.makeDefaultCfg.hasCorrectContents.primativeTypes_Comments_Inline",
                                #     "src/tests/testConfigs/dataclasses/makeDefaultCfg/hasCorrectContents/primativeTypes_Comments_Inline.toml"),
                                # ("testModules.dataclasses.makeDefaultCfg.hasCorrectContents.primativeTypes_Comments_Preceeding",
                                #     "src/tests/testConfigs/dataclasses/makeDefaultCfg/hasCorrectContents/primativeTypes_Comments_Preceeding.toml"),

                                ("testModules.dataclasses.makeDefaultCfg.hasCorrectContents.serializableTypes",
                                    "src/tests/testConfigs/dataclasses/makeDefaultCfg/hasCorrectContents/serializableTypes.toml"),
                                # ("testModules.dataclasses.makeDefaultCfg.hasCorrectContents.serializableTypes_Comments_Inline",
                                #     "src/tests/testConfigs/dataclasses/makeDefaultCfg/hasCorrectContents/serializableTypes_Comments_Inline.toml"),
                                # ("testModules.dataclasses.makeDefaultCfg.hasCorrectContents.serializableTypes_Comments_Preceeding",
                                #     "src/tests/testConfigs/dataclasses/makeDefaultCfg/hasCorrectContents/serializableTypes_Comments_Preceeding.toml")
                            ])
def test_makeDefaultCfg_hasCorrectContents(testModulePath, expectedOutputPath):
    setupTempDir()
    testModule = importlib.import_module(testModulePath)
    outputPath = f"{TESTS_TEMP_DIR}/test_dataclasses__makeDefaultCfg_hasCorrectContents.toml"

    with open(expectedOutputPath, "r") as f:
        expectedConfigContent = f.read()

    assert not os.path.isfile(outputPath)
    carica.makeDefaultCfg(testModule, fileName=outputPath)
    
    with open(outputPath, "r") as f:
        generatedConfigContent = f.read()

    assert expectedConfigContent == generatedConfigContent

    cleanupTempDir()


@pytest.mark.parametrize(("testModulePath", "expectedException"),
                            [
                                ("testModules.dataclasses.makeDefaultCfg.rejectsInvalid.nonSerializable",
                                    carica.exceptions.NonSerializableObject),
                                ("testModules.dataclasses.makeDefaultCfg.rejectsInvalid.nonStringMappingKey",
                                    carica.exceptions.NonStringMappingKey),
                                ("testModules.dataclasses.makeDefaultCfg.rejectsInvalid.multiTypeList",
                                    carica.exceptions.MultiTypeList)
                            ])
def test_makeDefaultCfg_rejectsInvalid(testModulePath, expectedException):
    setupTempDir()
    testModule = importlib.import_module(testModulePath)
    outputPath = f"{TESTS_TEMP_DIR}/test_dataclasses_makeDefaultCfg_rejectsInvalid.toml"

    with pytest.raises(expectedException):
        carica.makeDefaultCfg(testModule, fileName=outputPath)
    
    cleanupTempDir()


@pytest.mark.parametrize(("testModulePath", "testConfigPath"),
                            [
                                ("testModules.dataclasses.loadCfg.respectsTypeOverride.primativeTypes",
                                    "src/tests/testConfigs/dataclasses/loadCfg/respectsTypeOverride/primativeTypes.toml"),
                                ("testModules.dataclasses.loadCfg.respectsTypeOverride.serializableTypes",
                                    "src/tests/testConfigs/dataclasses/loadCfg/respectsTypeOverride/serializableTypes.toml"),
                                ("testModules.dataclasses.loadCfg.respectsTypeOverride.mutableTypes",
                                    "src/tests/testConfigs/dataclasses/loadCfg/respectsTypeOverride/mutableTypes.toml")
                            ])
def test_loadCfg_respectsTypeOverride(testModulePath, testConfigPath):
    testModule = importlib.import_module(testModulePath)
    with open(testConfigPath, "r") as f:
        testConfigValues = tomlkit.loads(f.read())

    # Make sure at least one field in the config is a SerializableDataClass
    cfgHasDataClass = False
    typeOverriddenFields: Dict[str, Dict[str, typeChecking.TypeHint]] = {}

    for varName, setValue in testConfigValues.items():
        if not isinstance(setValue, AbstractTable): continue

        defaultValue = getattr(testModule, varName)
        if isinstance(defaultValue, carica.models.SerializableDataClass):
            cfgHasDataClass = True

            # Make sure the test config actually changes something
            # and make sure the table contains a type-overridden field
            for fieldName, fieldValue in setValue.items():
                if fieldValue != getattr(defaultValue, fieldName) and defaultValue._fieldTypeIsOverridden(fieldName):
                    if varName not in typeOverriddenFields: typeOverriddenFields[varName] = {}
                    typeOverriddenFields[varName].update({fieldName: defaultValue._overriddenTypeOfFieldNamed(fieldName)})

    if not cfgHasDataClass:
        raise ValueError("Functionality not tested - no SerializableDataClass detected")
    if not typeOverriddenFields:
        raise ValueError("Functionality not tested - no SerializableDataClass field value changed by config file, or no field type overriden in config module")

    carica.loadCfg(testModule, testConfigPath)

    # Make sure the config values were loaded in
    for varName, overriddenFields in typeOverriddenFields.items():
        loadedVar = getattr(testModule, varName)
        for fieldName, fieldType in overriddenFields.items():
            # This will only test at a shallow level
            # i.e generic parameters are not tested
            assert isinstance(getattr(loadedVar, fieldName), fieldType if not hasattr(fieldType, "__origin__") else fieldType.__origin__) # type: ignore
