"""어절 단위 근사. 형태소 분석기 없이 조사와 어미 꼬리 사전으로 명사 어절을 가려낸다.

한계는 정직하게 적는다. 꼬리 사전에 없는 어미로 끝나는 어절은 명사로 오인할 수 있다. 그래서 명사 나열
임계를 다섯으로 두고, 쉼표와 괄호는 나열의 표지라 연속을 끊는다 (실측: 004 에서 표층 오탐 2건이 전부 쉼표 나열).

띄어 쓴 조사 (`hanlint 는`, `report 와 rules 와`) 와 계사 (`이고`, `인`) 는 앞 어절에 붙은 것으로 본다. 영문
어절이 이어지면 (`This sheet is too large`) 한 덩어리로 세어 영어 구절을 한국어 명사 나열로 오인하지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

from ...data import loadLines

HANGUL = re.compile(r"[가-힣]")
WORD_CHARS = re.compile(r"^[가-힣A-Za-z0-9]+$")
GENITIVE = re.compile(r"([가-힣]+)의(?=[\s,.)\]]|$)")
SPACED_GENITIVE = re.compile(r"(?<=\s)의(?=\s)")
COPULA = re.compile(r"^(?:이(?:고|며|다|라|란|면|라서|므로|지만|어서|었다|었고)|인|인데|입니다|였다)$")
DIGITS = re.compile(r"^\d+$")
OPENERS = "([{\"“‘'"
CLOSERS = ",.?!;:)]}\"”’'"
EDGE_PUNCTUATION = ".,?!:;\"'“”‘’()[]{}<>"


@dataclass(frozen=True)
class Word:
    core: str
    """앞뒤 부호를 뗀 어절."""
    endsClause: bool
    """어절 뒤에 쉼표, 종결 부호, 닫는 괄호가 붙어 있었는가. 나열과 절의 경계다."""
    opens: bool = False
    """어절 앞에 여는 괄호나 따옴표가 있었는가. 새 덩어리의 시작이다."""
    particle: bool = False
    """띄어 쓴 조사나 계사인가. 앞 어절에 붙은 것으로 본다."""


@cache
def tails(name: str) -> tuple[str, ...]:
    return tuple(sorted(loadLines(name), key=len, reverse=True))


@cache
def josaSet() -> frozenset[str]:
    return frozenset(loadLines("josa.txt"))


@cache
def euiNouns() -> frozenset[str]:
    return frozenset(loadLines("euiNouns.txt"))


@cache
def numerals() -> frozenset[str]:
    return frozenset(line.partition("\t")[0] for line in loadLines("koreanNumbers.txt"))


def isNumeral(core: str) -> bool:
    return core in numerals() or bool(DIGITS.match(core))


def words(text: str) -> list[Word]:
    result: list[Word] = []
    for raw in text.split():
        core = raw.strip(EDGE_PUNCTUATION)
        particle = core in josaSet() or bool(COPULA.match(core))
        result.append(Word(core, raw[-1] in CLOSERS, raw[0] in OPENERS, particle))
    return result


def tailOf(core: str, name: str) -> str | None:
    for tail in tails(name):
        if core.endswith(tail) and len(core) > len(tail):
            return tail
    return None


def stripJosa(core: str) -> str:
    tail = tailOf(core, "josa.txt")
    return core[: -len(tail)] if tail else core


def isBareNoun(core: str) -> bool:
    """조사도 어미도 붙지 않은 한글, 영문, 숫자 어절인가."""
    if not core or not WORD_CHARS.match(core):
        return False
    if not HANGUL.search(core):
        return True
    return tailOf(core, "josa.txt") is None and tailOf(core, "verbTails.txt") is None


def longestNounRun(text: str) -> int:
    """명사 어절 연속의 최대 길이. 수사와 바로 뒤의 단위 (여덟 개) 는 수량이라 세지도 끊지도 않는다."""
    longest = run = 0
    previousAscii = False
    afterNumeral = False
    for word in words(text):
        if word.opens:
            run, previousAscii = 0, False
        transparent = isNumeral(word.core) or afterNumeral
        afterNumeral = isNumeral(word.core)
        if word.particle or not isBareNoun(word.core):
            run, previousAscii = 0, False
        elif not transparent:
            isAscii = not HANGUL.search(word.core)
            if not (isAscii and previousAscii):
                run += 1
            previousAscii = isAscii
            longest = max(longest, run)
        if word.endsClause:
            run, previousAscii = 0, False
    return longest


def euiCount(text: str) -> int:
    """관형격 조사 의 의 수. 정의, 회의 처럼 의 로 끝나는 낱말은 빼고 띄어 쓴 의 는 센다."""
    attached = sum(1 for m in GENITIVE.finditer(text) if m.group(1) + "의" not in euiNouns())
    return attached + len(SPACED_GENITIVE.findall(text))


def syllableRange(initial: int, vowel: int) -> str:
    """초성과 중성이 정해진 한글 음절 28개 (종성 없음부터 ㅎ 까지) 의 정규식 범위."""
    first = 0xAC00 + (initial * 21 + vowel) * 28
    return chr(first) + "-" + chr(first + 27)


# 지 는 뒤 어미와 한 음절로 줄어든다. 되어진다, 되어졌다, 되어집니다 의 진, 졌, 집 이 전부 지 다.
# ㅈ 초성 (12) 에 ㅣ 중성 (20) 이거나 ㅕ 중성 (6) 인 음절 부류로 잡는다.
PASSIVE_TAIL = "[" + syllableRange(12, 20) + syllableRange(12, 6) + "]"


@cache
def doublePassivePattern() -> re.Pattern[str]:
    """피동 어간에 -어 를 붙인 표층형 뒤에 지 부류 음절. 어간 끝 이→여, 히→혀, 리→려, 기→겨, 그 밖에 +어."""
    stems = ["되어"]
    contraction = {"이": "여", "히": "혀", "리": "려", "기": "겨"}
    for stem in loadLines("passiveStems.txt"):
        last = stem[-1]
        stems.append(stem[:-1] + contraction[last] if last in contraction else stem + "어")
    alternatives = "|".join(sorted(stems, key=len, reverse=True))
    return re.compile("(" + alternatives + ")" + PASSIVE_TAIL)


def doublePassives(text: str) -> list[str]:
    """이중 피동의 표층형을 `되어지` 꼴로 정규화해 준다. kiwi 분석기와 같은 모양이다."""
    return [stem + "지" for stem in doublePassivePattern().findall(text)]
