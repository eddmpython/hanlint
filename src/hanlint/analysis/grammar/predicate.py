"""서술어의 형태. 문장 끝 어절을 (어간, 종류, 시제, 서법) 으로 풀고 원하는 문체로 다시 짠다.

**무엇을 하나.** `확인합니다` 를 풀면 어간 `확인하`, 동사, 현재, 평서다. 그것을 한다체로 짜면 `확인한다`,
해요체로 짜면 `확인해요` 다. 본보기와 문형을 그 글의 문체로 보이는 일 (문체 맞춤) 과 후보를 그 글의
문체로 내는 일이 전부 이 함수 둘 위에 선다.

**무엇을 안 하나.** 뜻은 보지 않는다. 동사와 형용사는 표층으로 갈리지 않으므로 `data/adjectiveStems.txt`
목록이 정한다. ㄹ 받침 어간은 합니다체와 한다체에서 ㄹ 이 사라져 `여` 와 `열` 이 같아 보이므로
`data/rieulStems.txt` 가 정한다. 목록에 없으면 동사이고 ㄹ 이 없는 것으로 본다. 그 판단이 틀리는 자리는
말뭉치의 왕복 시험 (한다체 → 합니다체 → 한다체 가 원문으로 돌아오는가) 이 잰다.

**해요체는 풀지 않는다.** `봐요` 의 어간은 `보` 이고 `써요` 의 어간은 `쓰` 인데 표층에서는 되돌릴 수 없는
자리가 많다 (`들어요` 는 들다인지 듣다인지 모른다). 짜는 것은 세 문체 전부, 푸는 것은 합니다체와 한다체다.

범위는 실측이 정했다. 기준 말뭉치 17,420문장의 평서 종결형 가운데 합니다체 1,992건과 한다체
12,255건을 풀었다. 같은 문체로 원문을 다시 만든 것은 각각 1,992건과 12,209건이다. 남은 46건은
옛 표기, 중의적인 `적다`, 한 번 나온 붙여 쓴 합성형처럼 표층만으로 확정하지 않은 자리다 (2026-08-28).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from ...data import loadLines
from . import hangul

VERB = "동사"
ADJECTIVE = "형용사"
COPULA = "계사"

PRESENT = "현재"
PAST = "과거"
FUTURE = "미래"
"""`겠` 이 붙은 것. 추측과 의지를 가르지 않는다. 짤 때 모양이 같다."""

DECLARATIVE = "평서"
QUESTION = "의문"
KKA_QUESTION = "까의문"
"""`생겼을까요` 처럼 `까` 로 끝나는 물음. 한다체는 `요` 만 떼고 나머지 둘은 `요` 를 붙인다."""
IMPERATIVE = "명령"
PROPOSITIVE = "청유"

HAPNIDA = "합니다"
HANDA = "한다"
HAEYO = "해요"
REGISTERS = (HAPNIDA, HANDA, HAEYO)

HAE_IRREGULAR = {"그렇": "그래", "이렇": "이래", "저렇": "저래", "어떻": "어때"}
"""ㅎ 불규칙 가운데 ㅓ 가 ㅔ 가 아니라 ㅐ 로 가는 넷. 나머지 ㅎ 불규칙은 ㅏ→ㅐ, ㅓ→ㅔ 다."""


@dataclass(frozen=True)
class Predicate:
    base: str
    """어간. 과거와 미래의 표지 (었, 겠) 까지 붙어 있다. 계사면 앞의 명사다."""
    kind: str
    """동사, 형용사, 계사."""
    tense: str = PRESENT
    mood: str = DECLARATIVE
    explicitCopula: bool = False
    """모음 뒤에서도 `예시이다`처럼 이가 드러난 한다체 계사인가. 원문을 글자 그대로 되짚는 데 쓴다."""


@cache
def adjectiveStems() -> tuple[str, ...]:
    return tuple(loadLines("adjectiveStems.txt"))


@cache
def rieulStems() -> frozenset[str]:
    return frozenset(loadLines("rieulStems.txt"))


@cache
def iVerbStems() -> frozenset[str]:
    return frozenset(loadLines("iVerbStems.txt"))


@cache
def irregularStems() -> tuple[tuple[str, str], ...]:
    """(어간, 부류). 긴 어간부터 대조한다."""
    rows = []
    for line in loadLines("irregularStems.txt"):
        stem, _, kind = line.partition("\t")
        rows.append((stem, kind))
    return tuple(sorted(rows, key=lambda r: -len(r[0])))


def isAdjective(stem: str) -> bool:
    """형용사 어간인가. 어간 전체가 목록에 있어야 한다.

    꼬리 일치는 안 된다. 실측: `발급하` 가 `급하` 로 형용사가 되어 `발급한다` 를 `발급하다` 로 되돌렸다.
    `불필요하` 같은 합성은 목록에 통째로 적는다.
    """
    return stem in adjectiveSet()


@cache
def adjectiveSet() -> frozenset[str]:
    return frozenset(adjectiveStems())


def irregularClass(stem: str) -> str | None:
    for known, kind in irregularStems():
        if stem == known or stem.endswith(known):
            return kind
    return None


def restoreRieul(base: str) -> str:
    """ㄹ 이 떨어진 어간을 되돌린다. 어간 전체가 목록에 있을 때만이다."""
    last = hangul.lastSyllable(base)
    if last is None or hangul.finalOf(last) != hangul.NONE:
        return base
    candidate = base[:-1] + hangul.withFinal(last, hangul.RIEUL)
    return candidate if candidate in rieulStems() else base


def stripEu(base: str) -> str:
    """`넣으세요` 의 매개 모음 `으` 를 뗀다. 받침 있는 음절 뒤의 `으` 만이다."""
    if len(base) >= 2 and base[-1] == "으" and hangul.isSyllable(base[-2]) and hangul.finalOf(base[-2]) != hangul.NONE:
        return base[:-1]
    return base


def tenseOf(base: str) -> str:
    """`했`, `됐`, `었` 처럼 ㅆ 받침이면 과거, `겠` 이면 미래. `있` 은 ㅆ 받침이지만 어간이다."""
    last = hangul.lastSyllable(base)
    if base.endswith("겠"):
        return FUTURE
    if last is not None and last != "있" and hangul.finalOf(last) == hangul.SSANGSIOT:
        return PAST
    return PRESENT


AUX_LINKS = ("지는", "지도", "지만", "지")
"""`않` 앞의 연결 어미. 뒤에 붙은 보조사 (`같지는 않다`) 까지 뗀다."""


def kindOf(base: str, previous: str | None) -> str:
    """현재형 어간의 종류. `않` 은 앞 어절 (`크지`, `같지는`) 의 종류를 이어받는다."""
    if base == "않" and previous:
        for link in AUX_LINKS:
            if previous.endswith(link) and len(previous) > len(link):
                return ADJECTIVE if isAdjective(previous[: -len(link)]) else VERB
    return ADJECTIVE if isAdjective(base) else VERB


def classify(base: str, previous: str | None, mood: str) -> Predicate | None:
    if not base:
        return None
    tense = tenseOf(base)
    kind = VERB if tense != PRESENT else kindOf(base, previous)
    return Predicate(base, kind, tense, mood)


def endsWithFinal(word: str, offset: int, final: int) -> bool:
    """뒤에서 `offset` 번째 글자가 그 받침을 가진 한글 음절인가."""
    if len(word) < offset:
        return False
    ch = word[-offset]
    return hangul.isSyllable(ch) and hangul.finalOf(ch) == final


def stemBefore(word: str, offset: int) -> str:
    """뒤에서 `offset` 번째 글자까지의 어간에서 그 글자의 받침을 뗀 것. `봅니다` 에서 `보`, `본다` 에서 `보`."""
    ch = word[-offset]
    return word[:-offset] + hangul.withFinal(ch, hangul.NONE)


def copulaOrIVerb(noun: str, mood: str) -> Predicate:
    """`보입니다` 가 계사인지 `이` 로 끝나는 동사인지. 동사 어간 목록이 정한다."""
    stem = noun + "이"
    # 어간 전체가 맞아야 한다. 꼬리 일치는 `후보입니다` 를 보이다로, `것들입니다` 를 들이다로 만들었다
    if stem in iVerbStems():
        return Predicate(stem, VERB, mood=mood)
    return Predicate(noun, COPULA, mood=mood)


def parsePredicate(word: str, previous: str | None = None) -> Predicate | None:
    """문장 끝 어절 하나를 푼다. 부호는 이미 뗀 것이어야 한다. 못 풀면 None.

    `previous` 는 앞 어절이다. `크지 않습니다` 의 `않` 이 형용사인지 동사인지를 거기서 읽는다.
    """
    if not word or not hangul.isSyllable(word[-1]):
        return None
    if word in ("다", "입니다") and previous:
        # `정본은 hanlint 다.` 처럼 띄어 쓴 영문이나 숫자 뒤의 계사. 앞 어절은 그대로 두고 어미만 짠다
        return Predicate("", COPULA)
    if word == "아닙니다" or word == "아니다":
        return Predicate("아니", ADJECTIVE)
    # 합니다체
    if word.endswith("입니다") and len(word) > 3:
        return copulaOrIVerb(word[:-3], DECLARATIVE)
    if word.endswith("입니까") and len(word) > 3:
        return copulaOrIVerb(word[:-3], QUESTION)
    if word.endswith("습니다"):
        return classify(word[:-3], previous, DECLARATIVE)
    if word.endswith("습니까"):
        return classify(word[:-3], previous, QUESTION)
    if word.endswith("니다") and endsWithFinal(word, 3, hangul.BIEUP):
        return classify(restoreRieul(stemBefore(word, 3)), previous, DECLARATIVE)
    if word.endswith("니까") and endsWithFinal(word, 3, hangul.BIEUP):
        return classify(restoreRieul(stemBefore(word, 3)), previous, QUESTION)
    if word.endswith("까요") and len(word) > 2:
        return Predicate(word[:-1], VERB, mood=KKA_QUESTION)
    if word.endswith("십시오") and len(word) > 3:
        return Predicate(restoreRieul(stripEu(word[:-3])), VERB, mood=IMPERATIVE)
    if word.endswith("세요") and len(word) > 2:
        return Predicate(restoreRieul(stripEu(word[:-2])), VERB, mood=IMPERATIVE)
    if word.endswith("읍시다"):
        return Predicate(word[:-3], VERB, mood=PROPOSITIVE)
    if word.endswith("시다") and endsWithFinal(word, 3, hangul.BIEUP):
        return Predicate(restoreRieul(stemBefore(word, 3)), VERB, mood=PROPOSITIVE)
    # 한다체
    if word.endswith("는다") and len(word) > 2:
        return Predicate(word[:-2], VERB)
    if word.endswith("는가") and len(word) > 2:
        return classify(word[:-2], previous, QUESTION)
    if word.endswith("자") and len(word) > 1:
        stem = restoreRieul(word[:-1])
        # `글자` 처럼 자 로 끝나는 명사와 갈라야 한다. 하자, 보자, 그리고 ㄹ 어간 목록의 것만 청유로 본다
        if stem.endswith(("하", "보")) or stem in rieulStems():
            return Predicate(stem, VERB, mood=PROPOSITIVE)
    if word.endswith("다") and len(word) > 1:
        stem = word[:-1]
        last = stem[-1]
        if hangul.isSyllable(last) and hangul.finalOf(last) == hangul.NIEUN and not word.endswith("이다"):
            return Predicate(restoreRieul(stemBefore(stem, 1)), VERB)
        tense = tenseOf(stem)
        if tense != PRESENT:
            return Predicate(stem, VERB, tense)
        if word.endswith("이다") and len(word) > 2:
            return Predicate(word[:-2], COPULA, explicitCopula=True)
        if stem == "않":
            return Predicate(stem, kindOf(stem, previous))
        if isAdjective(stem):
            return Predicate(stem, ADJECTIVE)
        return Predicate(stem, COPULA)
    return None


def conjugate(stem: str) -> str:
    """어간에 `아/어` 를 붙인 꼴. 축약과 불규칙을 반영한다. 해요체와 청유형과 과거형이 여기서 나온다."""
    if stem == "아니":
        return "아니에"
    if stem.endswith("하"):
        return stem[:-1] + "해"
    last = hangul.lastSyllable(stem)
    if last is None:
        return stem + "어"
    initial, vowel, final = hangul.split(last)
    kind = irregularClass(stem)
    if kind == "르" and len(stem) >= 2 and hangul.isSyllable(stem[-2]):
        before = stem[-2]
        bright = hangul.vowelOf(before) in hangul.BRIGHT
        return stem[:-2] + hangul.withFinal(before, hangul.RIEUL) + ("라" if bright else "러")
    if kind == "ㅂ":
        return stem[:-1] + hangul.withFinal(last, hangul.NONE) + "워"
    if kind == "ㅂ와":
        return stem[:-1] + hangul.withFinal(last, hangul.NONE) + "와"
    if kind == "ㄷ":
        return stem[:-1] + hangul.withFinal(last, hangul.RIEUL) + ("아" if vowel in hangul.BRIGHT else "어")
    if kind == "ㅅ":
        return stem[:-1] + hangul.withFinal(last, hangul.NONE) + ("아" if vowel in hangul.BRIGHT else "어")
    if kind == "ㅎ":
        for known, changed in HAE_IRREGULAR.items():
            if stem.endswith(known):
                return stem[: -len(known)] + changed
        opened = hangul.withFinal(last, hangul.NONE)
        target = {hangul.A: hangul.AE, hangul.YA: hangul.YAE, hangul.EO: hangul.E, hangul.YEO: hangul.YE}.get(vowel, hangul.AE)
        return stem[:-1] + hangul.withVowel(opened, target)
    if final != hangul.NONE:
        return stem + ("아" if vowel in hangul.BRIGHT else "어")
    if vowel in (hangul.A, hangul.YA, hangul.EO, hangul.YEO, hangul.AE, hangul.E, hangul.YE):
        return stem
    if vowel == hangul.OH:
        return stem[:-1] + hangul.withVowel(last, hangul.WA)
    if vowel == hangul.U:
        return stem[:-1] + hangul.withVowel(last, hangul.WO)
    if vowel == hangul.OE:
        return stem[:-1] + hangul.withVowel(last, hangul.WAE)
    if vowel == hangul.IH:
        return stem[:-1] + hangul.withVowel(last, hangul.YEO)
    if vowel == hangul.EU:
        before = stem[-2] if len(stem) >= 2 and hangul.isSyllable(stem[-2]) else None
        bright = before is not None and hangul.vowelOf(before) in hangul.BRIGHT
        return stem[:-1] + hangul.withVowel(last, hangul.A if bright else hangul.EO)
    return stem + "어"


def hasFinal(stem: str) -> int:
    """어간 마지막 음절의 받침. 한글이 아니면 받침 있는 것으로 다룬다 (`API이다`)."""
    last = hangul.lastSyllable(stem)
    return hangul.finalOf(last) if last is not None else hangul.MIEUM


def polite(stem: str) -> str:
    """합니다체 현재 서술형. 보→봅니다, 열→엽니다, 찾→찾습니다."""
    final = hasFinal(stem)
    if final == hangul.NONE or final == hangul.RIEUL:
        return stem[:-1] + hangul.withFinal(stem[-1], hangul.BIEUP) + "니다"
    return stem + "습니다"


def plainVerb(stem: str) -> str:
    """한다체 동사 현재. 보→본다, 열→연다, 찾→찾는다."""
    final = hasFinal(stem)
    if final == hangul.NONE or final == hangul.RIEUL:
        return stem[:-1] + hangul.withFinal(stem[-1], hangul.NIEUN) + "다"
    return stem + "는다"


def withEu(stem: str, ending: str) -> str:
    """`으` 매개 모음이 필요한 어미 (세요, 라, ㄴ가) 를 붙인다. 불규칙 어간은 아/어 앞과 같이 바뀐다."""
    final = hasFinal(stem)
    if final == hangul.NONE:
        return stem + ending
    if final == hangul.RIEUL:
        return (stem[:-1] + hangul.withFinal(stem[-1], hangul.NONE) if ending == "세요" else stem) + ending
    kind = irregularClass(stem)
    last = stem[-1]
    if kind in ("ㅂ", "ㅂ와"):
        return stem[:-1] + hangul.withFinal(last, hangul.NONE) + "우" + ending
    if kind == "ㄷ":
        return stem[:-1] + hangul.withFinal(last, hangul.RIEUL) + "으" + ending
    if kind == "ㅅ":
        return stem[:-1] + hangul.withFinal(last, hangul.NONE) + "으" + ending
    return stem + "으" + ending


def render(predicate: Predicate, register: str) -> str:
    """서술어를 그 문체로 짠다. 물음표와 마침표는 붙이지 않는다. 부른 쪽이 원래 부호를 다시 단다."""
    base, kind, tense, mood = predicate.base, predicate.kind, predicate.tense, predicate.mood
    if mood == KKA_QUESTION:
        return base if register == HANDA else base + "요"
    if tense != PRESENT:
        if register == HAPNIDA:
            return base + ("습니까" if mood == QUESTION else "습니다")
        if register == HANDA:
            return base + ("는가" if mood == QUESTION else "다")
        return base + "어요"
    if kind == COPULA:
        if not base:
            # 띄어 쓴 영문이나 숫자 뒤의 계사. 앞 어절을 모르므로 `이` 없는 꼴로 짠다
            return {HAPNIDA: "입니다", HANDA: "다", HAEYO: "예요"}[register]
        final = hasFinal(base)
        if register == HAPNIDA:
            return base + ("입니까" if mood == QUESTION else "입니다")
        if register == HANDA:
            if mood == QUESTION:
                return base + "인가"
            return base + ("이다" if predicate.explicitCopula or final != hangul.NONE else "다")
        return base + ("이에요" if final != hangul.NONE else "예요")
    if mood == IMPERATIVE:
        if register == HANDA:
            return withEu(base, "라")
        return withEu(base, "세요")
    if mood == PROPOSITIVE:
        if register == HAPNIDA:
            final = hasFinal(base)
            if final == hangul.NONE or final == hangul.RIEUL:
                return base[:-1] + hangul.withFinal(base[-1], hangul.BIEUP) + "시다"
            return base + "읍시다"
        if register == HANDA:
            return base + "자"
        return conjugate(base) + "요"
    if register == HAPNIDA:
        form = polite(base)
        return form[:-2] + "니까" if mood == QUESTION else form
    if register == HANDA:
        if kind == ADJECTIVE:
            if mood == QUESTION:
                final = hasFinal(base)
                if final == hangul.NONE or final == hangul.RIEUL:
                    return base[:-1] + hangul.withFinal(base[-1], hangul.NIEUN) + "가"
                return base + "은가"
            return base + "다"
        if mood == QUESTION:
            return (base[:-1] + hangul.withFinal(base[-1], hangul.NONE) if hasFinal(base) == hangul.RIEUL else base) + "는가"
        return plainVerb(base)
    return conjugate(base) + "요"
