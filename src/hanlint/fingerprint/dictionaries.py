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
}
GROUP_REF = re.compile(r"\$(\d)")


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
        re.compile(raw["pattern"]),
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
