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
    "screenSentence": "screenSentence.toml",
    "screenNarration": "screenNarration.toml",
    "screenTone": "screenTone.toml",
    "screenWord": "screenWord.toml",
}
GROUP_REF = re.compile(r"\$([0-9])")
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
    to: tuple[tuple[re.Pattern[str], str], ...] = ()
    """문장 전체를 다시 쓰는 (from, into) 규칙. 앞의 것부터 시도해 처음 맞는 것이 제안이다. 화면 문장 사전이 쓴다."""
    raw: str = ""
    """pattern 의 원문. 자리표시자를 펼치기 전의 글자라 두 판과 빈도표가 같은 키를 갖는다. 내장 항목만 갖고 설정으로
    더한 항목은 빈 글자라 어떤 종류의 관용으로도 접히지 않는다. 프로젝트가 스스로 넣은 낱말은 프로젝트가 짚고 싶은 것이다."""


def entryFrom(dictionary: str, raw: dict | str, builtin: bool = False) -> Entry:
    if isinstance(raw, str):
        raw = {"pattern": raw}
    return Entry(
        dictionary,
        re.compile(expandClasses(raw["pattern"])),
        raw.get("why", "설정에서 더한 항목"),
        raw.get("source", "설정"),
        raw.get("fix"),
        tuple((re.compile(expandClasses(source)), into) for source, into in raw.get("to", ())),
        raw["pattern"] if builtin else "",
    )


@cache
def builtinEntries() -> tuple[Entry, ...]:
    entries = []
    for dictionary, name in DICTIONARY_FILES.items():
        entries.extend(entryFrom(dictionary, raw, builtin=True) for raw in loadToml(name))
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


def rewriteBy(text: str, rules: tuple[tuple[re.Pattern[str], str], ...]) -> str | None:
    """to 규칙으로 문장을 다시 쓴다. 빈 그룹이 남긴 겹 공백은 하나로 줄이고 양끝을 다듬는다. 원문과 같으면 없다."""
    for pattern, into in rules:
        match = pattern.search(text)
        if match is None:
            continue
        rewritten = " ".join(applyFix(match, into).split())
        return rewritten if rewritten and rewritten != text else None
    return None


def matchesIn(text: str, entries: tuple[Entry, ...]) -> tuple[DictionaryMatch, ...]:
    found: list[DictionaryMatch] = []
    for entry in entries:
        for match in entry.pattern.finditer(text):
            fix = applyFix(match, entry.fix) if entry.fix else None
            rewrite = rewriteBy(text, entry.to) if entry.to else None
            found.append(
                DictionaryMatch(
                    entry.dictionary, match.group(0), match.start(), match.end(), entry.why, entry.source, fix, rewrite, entry.raw
                )
            )
    found.sort(key=lambda m: m.start)
    return tuple(found)
