import pytest
import carica
from caricaTestUtils import tokenizeLine


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
