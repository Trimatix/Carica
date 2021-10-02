from typing import Any, List
import tokenize

def tokenizeGenerator(gen):
    return [i for i in tokenize.generate_tokens(lambda: next(gen))]


def tokenizeLine(line: str):
    return tokenizeGenerator(iter([line]))


def tokenizeLines(testCases: List[str]):
    return tokenizeGenerator(iter(testCases))
