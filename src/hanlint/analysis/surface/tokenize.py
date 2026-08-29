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
HANGUL_WORD = re.compile(r"^[가-힣]+$")
WORD_CHARS = re.compile(r"^[가-힣A-Za-z0-9]+$")
GENITIVE = re.compile(r"([가-힣A-Za-z0-9]+|\))의(?=[\s,.)\]]|$)")
"""관형격 조사 의. 영문과 숫자 뒤 (API의, 600MiB의, 2054명의) 와 닫는 괄호 뒤 (L7(HTTP)의) 도 센다. 실측: 말뭉치
390편에서 형태소 분석기가 표층보다 euiChain 을 297건 더 잡았고 거의 전부가 그 두 자리였다 (2026-08-29)."""
SPACED_GENITIVE = re.compile(r"(?<=\s)의(?=\s)")
COPULA = re.compile(r"^(?:이(?:고|며|다|라|란|면|라서|므로|지만|어서|었다|었고)|인|인데|입니다|였다)$")
DIGITS = re.compile(r"^\d+$")
QUANTITY = re.compile(r"^제?\d[\d,.]*[가-힣]{1,3}$")
"""수에 단위가 붙은 어절 (2012년, 30분쯤, 제16호, 100명). 수량이라 명사 나열에서 세지도 끊지도 않는다. 실측: 말뭉치의
날짜와 시각 (`2012년 11월 29일 4시`) 이 명사 다섯으로 세어졌다 (2026-08-29)."""
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


@cache
def nonNouns() -> frozenset[str]:
    return frozenset(loadLines("nonNouns.txt"))


@cache
def inNouns() -> frozenset[str]:
    return frozenset(loadLines("inNouns.txt"))


def isCopulaAdnominal(core: str) -> bool:
    """`도구인`, `규모인` 처럼 명사에 계사 관형형 인 이 붙은 어절. 서술어라 명사 나열을 끊는다.

    어간이 두 음절 이상일 때만이다. 개인, 원인, 확인 은 어간이 한 음절이라 명사로 두고, 외국인 같은 세 음절 명사는
    data/inNouns.txt 가 뺀다. 실측: 말뭉치 390편에서 표층만 명사 다섯으로 본 15문장 가운데 넷이 이 꼴이었다 (2026-08-29).
    """
    return len(core) >= 3 and core.endswith("인") and bool(HANGUL_WORD.match(core)) and core not in inNouns()


def isNumeral(core: str) -> bool:
    return core in numerals() or bool(DIGITS.match(core))


def isQuantity(core: str) -> bool:
    """단위가 붙은 수. 수사와 달리 뒤 어절을 단위로 삼지 않는다."""
    return bool(QUANTITY.match(core))


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
    """명사 어절 연속의 최대 길이. 수사와 바로 뒤의 단위 (여덟 개) 는 수량이라 세지도 끊지도 않는다.

    의존명사와 관형사와 부사 (`수`, `몇`, `직접`) 는 조사도 어미도 안 붙어 표층으로는 명사로 보이지만
    명사 쌓기의 재료가 아니다. `data/nonNouns.txt` 가 그 목록이고 연속을 끊는다.
    """
    longest = run = 0
    previousAscii = False
    afterNumeral = False
    for word in words(text):
        if word.opens:
            run, previousAscii = 0, False
        transparent = isNumeral(word.core) or afterNumeral or isQuantity(word.core)
        afterNumeral = isNumeral(word.core)
        if word.particle or word.core in nonNouns() or not isBareNoun(word.core) or isCopulaAdnominal(word.core):
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


def genitiveSpans(text: str) -> list[tuple[int, int]]:
    """관형격 조사 의 가 붙은 자리 (시작, 끝). 정의, 회의 처럼 의 로 끝나는 낱말은 빼고 띄어 쓴 의 는 넣는다."""
    spans = [m.span() for m in GENITIVE.finditer(text) if m.group(1) + "의" not in euiNouns()]
    spans.extend(m.span() for m in SPACED_GENITIVE.finditer(text))
    return sorted(spans)


def euiCount(text: str) -> int:
    """관형격 조사 의 의 수."""
    return len(genitiveSpans(text))


def euiAdjacent(text: str) -> bool:
    """의 로 끝나는 어절 둘이 붙어 있는가 (회사의 팀의). 사이가 공백뿐이어야 한다. 정의 리소스의 처럼 앞이 의 로 끝나는
    낱말이면 아니다. 실측: 사용자 정의 리소스의 컨트롤러 가 인접으로 잡혔다 (2026-08-29)."""
    spans = genitiveSpans(text)
    return any(text[a:b].isspace() for (_, a), (b, _) in zip(spans, spans[1:], strict=False))


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
