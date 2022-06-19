import pytest
import carica
from carica import typeChecking
from carica.carica import BadTypeBehaviour, BadTypeHandling, ErrorHandling
from caricaTestUtils import tokenizeLine
import importlib
import os
import shutil
import tomlkit
from tomlkit import container


TESTS_TEMP_DIR = "testsTemp"


def cleanupTempDir():
    if os.path.isdir(TESTS_TEMP_DIR):
        shutil.rmtree(TESTS_TEMP_DIR)


def setupTempDir():
    cleanupTempDir()
    os.makedirs(TESTS_TEMP_DIR)


@pytest.mark.parametrize("testCase",
                            [
                                "basicInt = 1",
                                "basicStr = \"hello\"",
                                "multiLineStart = [\n]" # This is technically two lines, but the closing ] is
                            ])                          # needed for acceptance by the tokenizer
def test_lineStartsWithVariableIdentifier_TruePositive(testCase):
    assert carica.carica.lineStartsWithVariableIdentifier(tokenizeLine(testCase))


@pytest.mark.parametrize("testCase",
                            [
                                "if i == 1:",
                                "def myFunc():",
                                "import tokenize",
                                "# Some comment",
                                "return myVariable"
                                "myVariable",
                                "del myVariable",
                                "[myArray]",
                                "myDict[myName] = 1"
                            ])
def test_lineStartsWithVariableIdentifier_TrueNegative(testCase):
    assert not carica.carica.lineStartsWithVariableIdentifier(tokenizeLine(testCase))


@pytest.mark.parametrize(("testModulePath", "expectedNames"),
                            [
                                (
                                    "testModules.partialModuleVariables.TruePositive.basicTypes",
                                    {"intVar", "stringVar", "float_var"}
                                ),

                                (
                                    "testModules.partialModuleVariables.TruePositive.recursiveTypes",
                                    {"list_var", "dict_var", "setVar"}
                                ),
                                
                                (
                                    "testModules.partialModuleVariables.TruePositive.customTypes",
                                    {"myCustomType"}
                                )
                            ])
def test_partialModuleVariables_TruePositive(testModulePath, expectedNames):
    testModule = importlib.import_module(testModulePath)

    extractedVars = carica.carica._partialModuleVariables(testModule)

    for expectedName in expectedNames:
        assert expectedName in extractedVars
        assert extractedVars[expectedName].value == getattr(testModule, expectedName)

    for extractedName in extractedVars:
        assert extractedName in extractedVars


@pytest.mark.parametrize(("testModulePath", "expectedNames"),
                            [
                                (
                                    "testModules.partialModuleVariables.TrueNegative.basicTypes",
                                    {}
                                ),

                                (
                                    "testModules.partialModuleVariables.TrueNegative.recursiveTypes",
                                    {}
                                ),
                                
                                (
                                    "testModules.partialModuleVariables.TrueNegative.customTypes",
                                    {}
                                ),

                                (
                                    "testModules.partialModuleVariables.TrueNegative.hintsOnly",
                                    {}
                                )
                            ])
def test_partialModuleVariables_TrueNegative(testModulePath, expectedNames):
    testModule = importlib.import_module(testModulePath)

    extractedVars = carica.carica._partialModuleVariables(testModule)

    for expectedName in expectedNames:
        assert expectedName in extractedVars
        assert extractedVars[expectedName].value == getattr(testModule, expectedName)

    for extractedName in extractedVars:
        assert extractedName in extractedVars


@pytest.mark.parametrize(("testModulePath", "expectedComments"),
                            [
                                (
                                    "testModules.partialModuleVariables.Comments_Preceeding_TruePositive.singleComment",
                                    {"intVar": ["my intVar comment"], "float_var": ["my floatVar comment"]}
                                ),

                                (
                                    "testModules.partialModuleVariables.Comments_Preceeding_TruePositive.multiComment",
                                    {"myCustomType": ["my myCustomType comment", "but it has multiple lines",
                                                        "even has a third one"]}
                                )
                            ])
def test_partialModuleVariables_Comments_Preceeding_TruePositive(testModulePath, expectedComments):
    testModule = importlib.import_module(testModulePath)

    extractedVars = carica.carica._partialModuleVariables(testModule)

    for extractedName, extractedVar in extractedVars.items():
        if extractedName in expectedComments:
            assert extractedVar.preComments == expectedComments[extractedName]


@pytest.mark.parametrize(("testModulePath", "expectedComments"),
                            [
                                (
                                    "testModules.partialModuleVariables.Comments_Preceeding_TrueNegative.singleComment",
                                    {"intVar": [], "stringVar": [], "float_var": []}
                                ),

                                (
                                    "testModules.partialModuleVariables.Comments_Preceeding_TrueNegative.multiComment",
                                    {"myCustomType": []}
                                ),
                                
                                (
                                    "testModules.partialModuleVariables.Comments_Preceeding_TrueNegative.noComment",
                                    {"list_var": [], "dict_var": [], "setVar": []}
                                )
                            ])
def test_partialModuleVariables_Comments_Preceeding_TrueNegative(testModulePath, expectedComments):
    testModule = importlib.import_module(testModulePath)

    extractedVars = carica.carica._partialModuleVariables(testModule)

    for extractedName, extractedVar in extractedVars.items():
        assert extractedName in expectedComments
        if extractedName in expectedComments:
            assert extractedVar.preComments == expectedComments[extractedName]


@pytest.mark.parametrize(("testModulePath", "expectedComments"),
                            [
                                (
                                    "testModules.partialModuleVariables.Comments_Inline_TruePositive.singleComment",
                                    {"intVar": ["my intvar comment"], "stringVar": ["my stringvar comment"],
                                    "float_var": ["an inline comment"]}
                                )
                            ])
def test_partialModuleVariables_Comments_Inline_TruePositive(testModulePath, expectedComments):
    testModule = importlib.import_module(testModulePath)

    extractedVars = carica.carica._partialModuleVariables(testModule)

    for extractedName, extractedVar in extractedVars.items():
        assert extractedName in expectedComments
        assert extractedVar.inlineComments == expectedComments[extractedName]


@pytest.mark.parametrize(("testModulePath", "expectedComments"),
                            [
                                (
                                    "testModules.partialModuleVariables.Comments_Inline_TrueNegative.singleComment",
                                    {"intVar": [], "stringVar": [], "float_var": []}
                                ),
                                
                                (
                                    "testModules.partialModuleVariables.Comments_Inline_TrueNegative.noComment",
                                    {"list_var": [], "dict_var": [], "setVar": []}
                                )
                            ])
def test_partialModuleVariables_Comments_Inline_TrueNegative(testModulePath, expectedComments):
    testModule = importlib.import_module(testModulePath)

    extractedVars = carica.carica._partialModuleVariables(testModule)

    for extractedName, extractedVar in extractedVars.items():
        assert extractedName in expectedComments
        if extractedName in expectedComments:
            assert extractedVar.inlineComments == expectedComments[extractedName]


@pytest.mark.parametrize(("testModulePath", "outputPath", "giveOutputPath"),
                            [
                                ("testModules.emptyConfig", "defaultCfg.toml", False),
                                ("testModules.emptyConfig", "defaultCfg.toml", True),
                                ("testModules.emptyConfig", "myCfg.toml", True),
                                ("testModules.emptyConfig", f"{TESTS_TEMP_DIR}/myCfg.toml", True)
                            ])
def test_makeDefaultCfg_makesFile(testModulePath, outputPath, giveOutputPath):
    setupTempDir()
    testModule = importlib.import_module(testModulePath)

    assert not os.path.isfile(outputPath)
    if giveOutputPath:
        carica.makeDefaultCfg(testModule, fileName=outputPath)
    else:
        carica.makeDefaultCfg(testModule)

    assert os.path.isfile(outputPath)
    os.remove(outputPath)


# Preceeding comment tests disabled for now because this functionality is incomplete
@pytest.mark.parametrize(("testModulePath", "expectedOutputPath"),
                            [
                                ("testModules.makeDefaultCfg.hasCorrectContents.primativeTypes",
                                    "src/tests/testConfigs/makeDefaultCfg/hasCorrectContents/primativeTypes.toml"),
                                ("testModules.makeDefaultCfg.hasCorrectContents.primativeTypes_Comments_Inline",
                                    "src/tests/testConfigs/makeDefaultCfg/hasCorrectContents/primativeTypes_Comments_Inline.toml"),
                                # ("testModules.makeDefaultCfg.hasCorrectContents.primativeTypes_Comments_Preceeding",
                                #     "src/tests/testConfigs/makeDefaultCfg/hasCorrectContents/primativeTypes_Comments_Preceeding.toml"),

                                ("testModules.makeDefaultCfg.hasCorrectContents.serializableTypes",
                                    "src/tests/testConfigs/makeDefaultCfg/hasCorrectContents/serializableTypes.toml"),
                                ("testModules.makeDefaultCfg.hasCorrectContents.serializableTypes_Comments_Inline",
                                    "src/tests/testConfigs/makeDefaultCfg/hasCorrectContents/serializableTypes_Comments_Inline.toml"),
                                # ("testModules.makeDefaultCfg.hasCorrectContents.serializableTypes_Comments_Preceeding",
                                #     "src/tests/testConfigs/makeDefaultCfg/hasCorrectContents/serializableTypes_Comments_Preceeding.toml")
                            ])
def test_makeDefaultCfg_hasCorrectContents(testModulePath, expectedOutputPath):
    setupTempDir()
    testModule = importlib.import_module(testModulePath)
    outputPath = f"{TESTS_TEMP_DIR}/test_makeDefaultCfg_hasCorrectContents.toml"

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
                                ("testModules.makeDefaultCfg.rejectsInvalid.nonSerializable",
                                    carica.exceptions.NonSerializableObject),
                                ("testModules.makeDefaultCfg.rejectsInvalid.nonStringMappingKey",
                                    carica.exceptions.NonStringMappingKey),
                                ("testModules.makeDefaultCfg.rejectsInvalid.multiTypeList",
                                    carica.exceptions.MultiTypeList)
                            ])
def test_makeDefaultCfg_rejectsInvalid(testModulePath, expectedException):
    setupTempDir()
    testModule = importlib.import_module(testModulePath)
    outputPath = f"{TESTS_TEMP_DIR}/test_makeDefaultCfg_rejectsInvalid.toml"

    with pytest.raises(expectedException):
        carica.makeDefaultCfg(testModule, fileName=outputPath)
    
    cleanupTempDir()


@pytest.mark.parametrize(("testModulePath", "testConfigPath"),
                            [
                                ("testModules.loadCfg.loadsCorrectValues.primativeTypes",
                                    "src/tests/testConfigs/loadCfg/loadsCorrectValues/primativeTypes.toml"),
                                ("testModules.loadCfg.loadsCorrectValues.serializableTypes",
                                    "src/tests/testConfigs/loadCfg/loadsCorrectValues/serializableTypes.toml"),
                            ])
def test_loadCfg_loadsCorrectValues(testModulePath, testConfigPath):
    testModule = importlib.import_module(testModulePath)
    with open(testConfigPath, "r") as f:
        testConfigValues = tomlkit.loads(f.read())

    # Make sure the test config actually changes something
    assert not all(getattr(testModule, varName) == testConfigValues[varName] for varName in testConfigValues)

    carica.loadCfg(testModule, testConfigPath)

    # Make sure the config values were loaded in
    for varName in testConfigValues:
        assert carica.carica._serialize(getattr(testModule, varName), [varName]) == testConfigValues[varName]


@pytest.mark.parametrize(("testModulePath", "testConfigPath", "expectedException"),
                            [
                                ("testModules.loadCfg.rejectsInvalid.incorrectTypes_primativeTypes",
                                    "src/tests/testConfigs/loadCfg/rejectsInvalid/incorrectTypes_primativeTypes.toml",
                                    TypeError),
                                ("testModules.loadCfg.rejectsInvalid.incorrectTypes_serializableTypes",
                                    "src/tests/testConfigs/loadCfg/rejectsInvalid/incorrectTypes_serializableTypes.toml",
                                    TypeError),
                                ("testModules.loadCfg.rejectsInvalid.serializableTypes_serializeFail",
                                    "src/tests/testConfigs/loadCfg/rejectsInvalid/serializableTypes_serializeFail.toml",
                                    KeyError)
                            ])
def test_loadCfg_rejectsInvalid(testModulePath, testConfigPath, expectedException):
    testModule = importlib.import_module(testModulePath)

    with pytest.raises(expectedException):
        carica.loadCfg(testModule, testConfigPath)


@pytest.mark.parametrize(("testModulePath", "testConfigPath"),
                            [
                                ("testModules.loadCfg_typeCasting.loadsCorrectValues.primativeTypes",
                                    "src/tests/testConfigs/loadCfg_typeCasting/loadsCorrectValues/primativeTypes.toml")
                            ])
def test_loadCfg_typeCasting_loadsCorrectValues(testModulePath, testConfigPath):
    testModule = importlib.import_module(testModulePath)
    with open(testConfigPath, "r") as f:
        testConfigValues = tomlkit.loads(f.read())

    defaults = carica.carica._partialModuleVariables(testModule)

    # Make sure the test config actually has a variable of an incorrect type
    assert not all(type(getattr(testModule, varName)) == type(testConfigValues[varName]) for varName in testConfigValues)

    carica.loadCfg(testModule, testConfigPath)

    # Make sure the config values have not changed
    for varName in testConfigValues:
        assert carica.carica._serialize(getattr(testModule, varName), [varName]) == defaults[varName].value


@pytest.mark.parametrize(("testModulePath", "testConfigPath", "expectedException"),
                            [
                                ("testModules.loadCfg_typeCasting.rejectsInvalid.primativeTypes",
                                    "src/tests/testConfigs/loadCfg_typeCasting/rejectsInvalid/primativeTypes.toml",
                                    TypeError)
                            ])
def test_loadCfg_typeCasting_rejectsInvalid(testModulePath, testConfigPath, expectedException):
    testModule = importlib.import_module(testModulePath)
    with open(testConfigPath, "r") as f:
        testConfigValues = tomlkit.loads(f.read())

    # Make sure the test config actually has a variable of an incorrect type
    assert not all(type(getattr(testModule, varName)) == type(testConfigValues[varName]) for varName in testConfigValues)

    with pytest.raises(expectedException):
        carica.loadCfg(testModule, testConfigPath)


@pytest.mark.parametrize(("testModulePath", "testConfigPath"),
                            [
                                ("testModules.loadCfg_typeCasting.allowsCastFailKeeping.primativeTypes",
                                    "src/tests/testConfigs/loadCfg_typeCasting/allowsCastFailKeeping/primativeTypes.toml")
                            ])
def test_loadCfg_typeCasting_allowsCastFailKeeping(testModulePath, testConfigPath):
    testModule = importlib.import_module(testModulePath)
    with open(testConfigPath, "r") as f:
        testConfigValues = tomlkit.loads(f.read())

    defaults = carica.carica._partialModuleVariables(testModule)

    # Make sure the test config actually has a variable of an incorrect type
    assert not all(type(getattr(testModule, varName)) == type(testConfigValues[varName]) for varName in testConfigValues)

    badTypeHandling = BadTypeHandling()
    badTypeHandling.behaviour = BadTypeBehaviour.CAST
    badTypeHandling.rejectType = ErrorHandling.RAISE
    badTypeHandling.keepFailedCast = True
    badTypeHandling.logTypeKeeping = False
    badTypeHandling.logSuccessfulCast = False
    badTypeHandling.includeExceptionTrace = True

    carica.loadCfg(testModule, testConfigPath, badTypeHandling)

    # Make sure the config values have not changed
    for varName in defaults:
        loadedValue = testConfigValues[varName]
        if not isinstance(loadedValue, container.Container): continue
        assert carica.carica._serialize(getattr(testModule, varName), [varName]) == loadedValue.value


@pytest.mark.parametrize(("testModulePath", "testConfigPath"),
                            [
                                ("testModules.loadCfg.respectsTypeOverride.primativeTypes",
                                    "src/tests/testConfigs/loadCfg/respectsTypeOverride/primativeTypes.toml"),
                                ("testModules.loadCfg.respectsTypeOverride.serializableTypes",
                                    "src/tests/testConfigs/loadCfg/respectsTypeOverride/serializableTypes.toml"),
                            ])
def test_loadCfg_respectsTypeOverride(testModulePath, testConfigPath):
    testModule = importlib.import_module(testModulePath)
    with open(testConfigPath, "r") as f:
        testConfigValues = tomlkit.loads(f.read())

    # Make sure the test config actually changes something
    assert any(isinstance(getattr(testModule, varName), typeChecking._DeserializedTypeOverrideProxy) for varName in testConfigValues)

    carica.loadCfg(testModule, testConfigPath)

    # Make sure the config values were loaded in with the overridden type
    for varName in testConfigValues:
        if isinstance(getattr(testModule, varName), typeChecking._DeserializedTypeOverrideProxy):
            assert isinstance(testConfigValues[varName], getattr(testModule, varName).loadedType)
