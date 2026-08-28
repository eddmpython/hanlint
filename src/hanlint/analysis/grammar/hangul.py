"""한글 음절의 자모 산술. 형태 층 전체가 여기서 초성, 중성, 종성을 읽고 다시 짠다.

유니코드 한글 음절은 (초성 × 21 + 중성) × 28 + 종성 의 차례로 놓여 있어서 곱셈과 나눗셈으로 쪼개고
붙일 수 있다. 표를 안 두고 산술로 하는 것은 표가 틀릴 자리를 없애려는 것이다 (십의 종성을 ㄹ 로
적었던 적이 있다).
"""

from __future__ import annotations

BASE = 0xAC00
LAST = 0xD7A3
VOWELS = 21
FINALS = 28

# 중성 자리 번호. ㅏ ㅐ ㅑ ㅒ ㅓ ㅔ ㅕ ㅖ ㅗ ㅘ ㅙ ㅚ ㅛ ㅜ ㅝ ㅞ ㅟ ㅠ ㅡ ㅢ ㅣ 차례다.
A, AE, YA, YAE, EO, E, YEO, YE, OH, WA, WAE, OE, YO, U, WO, WE, WI, YU, EU, UI, IH = range(VOWELS)

# 종성 자리 번호 가운데 형태 층이 이름으로 부르는 것.
NONE = 0
GIYEOK = 1
NIEUN = 4
DIGEUT = 7
RIEUL = 8
MIEUM = 16
BIEUP = 17
SIOT = 19
SSANGSIOT = 20
IEUNG = 21
HIEUT = 27

BRIGHT = frozenset({A, OH, YA, YO, WA})
"""양성 모음. 이 모음 뒤에는 `아` 가 붙고 나머지에는 `어` 가 붙는다."""


def isSyllable(ch: str) -> bool:
    return len(ch) == 1 and BASE <= ord(ch) <= LAST


def split(ch: str) -> tuple[int, int, int]:
    """(초성, 중성, 종성) 자리 번호. 한글 음절이 아니면 ValueError."""
    if not isSyllable(ch):
        raise ValueError(f"한글 음절이 아니다: {ch!r}")
    code = ord(ch) - BASE
    return code // (VOWELS * FINALS), (code // FINALS) % VOWELS, code % FINALS


def join(initial: int, vowel: int, final: int = NONE) -> str:
    return chr(BASE + (initial * VOWELS + vowel) * FINALS + final)


def finalOf(ch: str) -> int | None:
    """음절의 종성 번호. 한글 음절이 아니면 None."""
    return split(ch)[2] if isSyllable(ch) else None


def vowelOf(ch: str) -> int | None:
    return split(ch)[1] if isSyllable(ch) else None


def withFinal(ch: str, final: int) -> str:
    initial, vowel, _ = split(ch)
    return join(initial, vowel, final)


def withVowel(ch: str, vowel: int) -> str:
    initial, _, final = split(ch)
    return join(initial, vowel, final)


def lastSyllable(word: str) -> str | None:
    """낱말의 마지막 한글 음절. 없으면 None."""
    return word[-1] if word and isSyllable(word[-1]) else None
