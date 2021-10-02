import pytest
import carica
from caricaTestUtils import tokenizeLine
import importlib


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
                                    "testModules.partialModuleVariables_TruePositive.basicTypes",
                                    {"intVar", "stringVar", "float_var"}
                                ),

                                (
                                    "testModules.partialModuleVariables_TruePositive.recursiveTypes",
                                    {"list_var", "dict_var", "setVar"}
                                ),
                                
                                (
                                    "testModules.partialModuleVariables_TruePositive.customTypes",
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
                                    "testModules.partialModuleVariables_TrueNegative.basicTypes",
                                    {}
                                ),

                                (
                                    "testModules.partialModuleVariables_TrueNegative.recursiveTypes",
                                    {}
                                ),
                                
                                (
                                    "testModules.partialModuleVariables_TrueNegative.customTypes",
                                    {}
                                ),

                                (
                                    "testModules.partialModuleVariables_TrueNegative.hintsOnly",
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
                                    "testModules.partialModuleVariables_Comments_Preceeding_TruePositive.singleComment",
                                    {"intVar": ["my intVar comment"], "float_var": ["my floatVar comment"]}
                                ),

                                (
                                    "testModules.partialModuleVariables_Comments_Preceeding_TruePositive.multiComment",
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
                                    "testModules.partialModuleVariables_Comments_Preceeding_TrueNegative.singleComment",
                                    {"intVar": [], "stringVar": [], "float_var": []}
                                ),

                                (
                                    "testModules.partialModuleVariables_Comments_Preceeding_TrueNegative.multiComment",
                                    {"myCustomType": []}
                                ),
                                
                                (
                                    "testModules.partialModuleVariables_Comments_Preceeding_TrueNegative.noComment",
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
