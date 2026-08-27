"""사전 넷을 한 번 컴파일하고 문장에서 맞는 자리를 찾는다. 설정의 dictionary 항목을 더한다."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

from ..config import Config
from ..data import loadToml
from .sentencePrint import DictionaryMatch

DICTIONARY_FILES = {
    "cliches": "cliches.toml",
    "translationese": "translationese.toml",
    "redundantPair": "redundantPair.toml",
    "japaneseLoan": "japaneseLoan.toml",
    "spelling": "spelling.toml",
    "spacing": "spacing.toml",
    "confusable": "confusable.toml",
    "easyWords": "easyWords.toml",
}
GROUP_REF = re.compile(r"\$(\d)")
FINALS = {"ㄴ": 4, "ㄹ": 8}
"""받침 자리표시자. {ㄹ} 은 ㄹ 받침으로 끝나는 음절 399개의 문자 부류로 펼쳐진다. 관형형 뒤의 의존 명사를 잡는다."""
JOSA_TAIL = "(?=(?:에서는|으로는|에서|에게|까지|부터|보다|처럼|으로|이나|은|는|이|가|을|를|의|에|로|와|과|도|만)?(?![가-힣]))"
"""{조사} 자리표시자. 낱말 뒤에 조사가 붙었거나 낱말이 끝나는 자리. 다른 낱말의 일부 (금일봉의 금일) 는 안 잡는다."""
PLACEHOLDER = re.compile(r"\{(ㄴ|ㄹ|조사)\}")


def syllableClass(final: str) -> str:
    chars = [chr(0xAC00 + (initial * 21 + vowel) * 28 + FINALS[final]) for initial in range(19) for vowel in range(21)]
    return "[" + "".join(chars) + "]"


def expandClasses(pattern: str) -> str:
    return PLACEHOLDER.sub(lambda m: JOSA_TAIL if m.group(1) == "조사" else syllableClass(m.group(1)), pattern)


@dataclass(frozen=True)
class Entry:
    dictionary: str
    pattern: re.Pattern[str]
    why: str
    source: str
    fix: str | None


def entryFrom(dictionary: str, raw: dict | str) -> Entry:
    if isinstance(raw, str):
        raw = {"pattern": raw}
    return Entry(
        dictionary,
        re.compile(expandClasses(raw["pattern"])),
        raw.get("why", "설정에서 더한 항목"),
        raw.get("source", "설정"),
        raw.get("fix"),
    )


@cache
def builtinEntries() -> tuple[Entry, ...]:
    entries = []
    for dictionary, name in DICTIONARY_FILES.items():
        entries.extend(entryFrom(dictionary, raw) for raw in loadToml(name))
    return tuple(entries)


def entriesFor(config: Config) -> tuple[Entry, ...]:
    extra = []
    for dictionary, items in config.dictionary.items():
        if dictionary not in DICTIONARY_FILES:
            raise ValueError(f"모르는 사전: {dictionary}. {', '.join(DICTIONARY_FILES)} 가운데 하나다")
        extra.extend(entryFrom(dictionary, raw) for raw in items)
    return builtinEntries() + tuple(extra)


def applyFix(match: re.Match[str], fix: str) -> str:
    return GROUP_REF.sub(lambda m: match.group(int(m.group(1))) or "", fix)


def matchesIn(text: str, entries: tuple[Entry, ...]) -> tuple[DictionaryMatch, ...]:
    found: list[DictionaryMatch] = []
    for entry in entries:
        for match in entry.pattern.finditer(text):
            fix = applyFix(match, entry.fix) if entry.fix else None
            found.append(
                DictionaryMatch(entry.dictionary, match.group(0), match.start(), match.end(), entry.why, entry.source, fix)
            )
    found.sort(key=lambda m: m.start)
    return tuple(found)
