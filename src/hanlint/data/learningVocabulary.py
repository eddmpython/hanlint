"""국립국어원 한국어 학습용 어휘 목록.

정본 자료와 필드 계약은 `learningVocabularySource.toml`, 재현 가능한 UTF-8 투영은
`learningVocabulary.tsv` 다. 이 등급은 한국어 학습자를 위한 것이며 모어 화자의 낱말 난도나 좋은 글의
점수가 아니다. 문맥으로 동형어를 가르지 않으므로 같은 표층형에 딸린 등급을 전부 보존한다.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from typing import Protocol

from .load import readText


class TermSentence(Protocol):
    line: int
    topics: frozenset[str]


class TermDocument(Protocol):
    sentences: tuple[TermSentence, ...]


@dataclass(frozen=True)
class VocabularyEntry:
    rank: int | None
    word: str
    lexeme: str
    partOfSpeech: str
    grade: str


@dataclass(frozen=True)
class Term:
    word: str
    line: int
    grades: tuple[str, ...]
    outside: bool = False

    def asDict(self) -> dict:
        data: dict = {"word": self.word, "line": self.line}
        if self.outside:
            data["outside"] = True
        else:
            data["grades"] = list(self.grades)
        return data


@cache
def vocabularyMetadata() -> dict:
    return tomllib.loads(readText("learningVocabularySource.toml"))


@cache
def vocabularyEntries() -> tuple[VocabularyEntry, ...]:
    lines = readText("learningVocabulary.tsv").splitlines()
    expected = "rank\tword\tlexeme\tpartOfSpeech\tgrade"
    if not lines or lines[0] != expected:
        raise ValueError(f"learningVocabulary.tsv 머리줄이 다르다: {lines[0] if lines else '비었다'}")
    entries: list[VocabularyEntry] = []
    for line in lines[1:]:
        rank, word, lexeme, partOfSpeech, grade = line.split("\t")
        entries.append(VocabularyEntry(int(rank) if rank else None, word, lexeme, partOfSpeech, grade))
    return tuple(entries)


@cache
def gradesByLexeme() -> dict[str, tuple[str, ...]]:
    found: dict[str, set[str]] = {}
    for entry in vocabularyEntries():
        found.setdefault(entry.lexeme, set()).add(entry.grade)
    return {word: tuple(sorted(grades)) for word, grades in found.items()}


def termsIn(document: TermDocument, includeOutside: bool = False) -> tuple[Term, ...]:
    """처음 나온 C 전용 화제어와, 요청했을 때 목록 밖 한글 화제어를 문서 순서대로 준다.

    A/C처럼 뜻에 따라 등급이 갈리는 표층형은 C라고 단정하지 않는다. 목록 밖은 전문어일 수도 고유명사일
    수도 있으므로 후보라고만 부른다. 화제어 추출의 표층 한계는 fingerprint/topics.py가 소유한다.
    """
    grades = gradesByLexeme()
    seen: set[str] = set()
    found: list[Term] = []
    for sentence in document.sentences:
        for word in sorted(sentence.topics):
            if word in seen:
                continue
            seen.add(word)
            # 한 글자는 조사 제거가 만든 가짜 어간 (`하는` → `하`) 이 섞인다. 용어 후보로는 가치가 낮아 뺀다.
            if len(word) < 2:
                continue
            wordGrades = grades.get(word)
            if wordGrades == ("C",):
                found.append(Term(word, sentence.line, wordGrades))
            elif includeOutside and wordGrades is None and word.isalpha() and not word.isascii():
                found.append(Term(word, sentence.line, (), outside=True))
    return tuple(found)
