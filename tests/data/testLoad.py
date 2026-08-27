"""사전과 표지 목록이 읽히고 형식이 맞는지. 사전 항목의 정규식이 컴파일되는지도 여기서 본다."""

import re

from hanlint.data import loadLines, loadPatterns, loadToml

DICTIONARIES = ("cliches.toml", "translationese.toml", "redundantPair.toml", "japaneseLoan.toml")
PATTERN_LISTS = (
    "causalMarkers.txt",
    "hedges.txt",
    "readerCalls.txt",
    "promiseMarkers.txt",
    "recallMarkers.txt",
    "deixis.txt",
)
PLAIN_LISTS = (
    "josa.txt",
    "verbTails.txt",
    "connectors.txt",
    "countUnits.txt",
    "stopwords.txt",
    "passiveStems.txt",
    "emphasisWords.txt",
)


def testLinesSkipCommentsAndBlanks():
    lines = loadLines("connectors.txt")
    assert "그리고" in lines
    assert not any(line.startswith("#") for line in lines)


def testEveryDictionaryEntryHasPatternAndWhy():
    for name in DICTIONARIES:
        entries = loadToml(name)
        assert entries, name
        for entry in entries:
            assert entry.get("pattern") and entry.get("why") and entry.get("source"), (name, entry)
            re.compile(entry["pattern"])


def testPatternListsCompile():
    for name in PATTERN_LISTS:
        assert loadPatterns(name), name


def testPlainListsAreNonEmpty():
    for name in PLAIN_LISTS:
        assert loadLines(name), name


def testEndingsHaveClassAndRegex():
    for line in loadLines("endings.txt"):
        kind, _, pattern = line.partition("\t")
        assert kind and pattern, line
        re.compile(pattern)


def testHoleKindsCoverEveryListedRuleOnce():
    seen: dict[str, str] = {}
    for kind in loadToml("holeKinds.toml"):
        for rule in kind["rules"]:
            assert rule not in seen, f"{rule} 이 {seen[rule]} 와 {kind['id']} 에 둘 다 있다"
            seen[rule] = kind["id"]
        assert len(kind["symbol"]) == 1
