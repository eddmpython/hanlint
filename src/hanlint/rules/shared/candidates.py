"""뜻을 고르지 않고 표층에서 셀 수 있는 후보를 만든다.

후보의 공통 형식은 text와 why 둘뿐이다. 규칙마다 다른 점수나 순위를 두지 않는다. 후보가 없으면 빈
튜플을 주며, 억지로 한 칸을 채우지 않는다.
"""

from __future__ import annotations

import re

from ...analysis.grammar import HAEYO, HANDA, HAPNIDA, REGISTERS, fitJosa, hangul
from ...analysis.grammar.predicate import conjugate, polite
from ...analysis.grammar.voice import decomposePassive
from ...analysis.surface.tokenize import stripJosa, words
from ...data import loadLines
from ...fingerprint import SentencePrint
from ..finding import Candidate

ENDING_CANDIDATES = {
    HAPNIDA: (("-습니까?", "같은 문체의 의문형"), ("-기 때문입니다", "같은 문체의 인과형")),
    HANDA: (("-는가?", "같은 문체의 의문형"), ("-기 때문이다", "같은 문체의 인과형")),
    HAEYO: (("-나요?", "같은 문체의 의문형"), ("-기 때문이에요", "같은 문체의 인과형")),
}


def longSentenceCandidates(text: str) -> tuple[Candidate, ...]:
    """연결 어미 뒤의 문장 경계 후보. 글자를 고쳐 쓰지는 않는다."""
    endings = sorted(loadLines("candidateSplitEndings.txt"), key=len, reverse=True)
    pattern = re.compile(r"(?P<word>[가-힣]+(?P<ending>" + "|".join(map(re.escape, endings)) + r"))[,;]?\s+")
    candidates = []
    for match in pattern.finditer(text):
        word = match.group("word")
        ending = match.group("ending")
        if word == "그리고" or len(word) <= len(ending):
            continue
        marked = text[: match.end()].rstrip() + " | " + text[match.end() :].lstrip()
        candidates.append(Candidate(marked, f"연결 어미 `{ending}` 뒤를 문장 경계로 검토한다"))
    return tuple(candidates)


def _replacementForDeixis(topic: str, deixis: str) -> str:
    if deixis.startswith("이것"):
        suffix = deixis[len("이것") :]
        return topic + fitJosa(topic, suffix)
    if deixis.startswith("해당 "):
        last = deixis.rsplit(maxsplit=1)[-1]
        base = stripJosa(last)
        suffix = last[len(base) :]
        return topic + fitJosa(topic, suffix)
    if deixis == "이러한":
        return topic + "의"
    if deixis == "이처럼":
        return topic + "처럼"
    return topic


def danglingDeixisCandidates(current: SentencePrint, previous: SentencePrint | None) -> tuple[Candidate, ...]:
    """앞 문장에 실제로 나온 화제어를 현재 지시어 자리에 넣은 후보."""
    if previous is None or not current.deixis:
        return ()
    deixis = current.deixis[0]
    topics = sorted(previous.topics, key=lambda topic: (previous.text.lower().find(topic), topic))
    return tuple(
        Candidate(
            current.text.replace(deixis, _replacementForDeixis(topic, deixis), 1),
            f"바로 앞 문장에 나온 명사 `{topic}`",
        )
        for topic in topics
    )


def nounPileCandidates(text: str) -> tuple[Candidate, ...]:
    """명사 나열 안에서 하다 동사로 되돌릴 수 있는 어근."""
    actionNouns = set(loadLines("candidateActionNouns.txt"))
    found = []
    for word in words(text):
        core = stripJosa(word.core)
        if core in actionNouns and core not in found:
            found.append(core)
    return tuple(Candidate(noun + "하다", f"명사 `{noun}`{fitJosa(noun, '을')} 동사 어근으로 되돌린다") for noun in found)


def endingRepeatCandidates(register: str) -> tuple[Candidate, ...]:
    """문서 문체 안에서 고를 수 있는 종결 꼴. 뜻이 맞는지는 고르는 쪽이 정한다."""
    target = register if register in REGISTERS else HAPNIDA
    return tuple(Candidate(text, why) for text, why in ENDING_CANDIDATES[target])


def _reducedPassiveText(text: str, surface: str, reduced: str) -> str | None:
    """외부 `지`의 활용을 첫 피동 어간에 옮긴 문장."""
    prefix = surface[:-1]
    start = 0
    while (at := text.find(prefix, start)) >= 0:
        tailAt = at + len(prefix)
        if tailAt >= len(text) or not hangul.isSyllable(text[tailAt]):
            start = at + 1
            continue
        initial, vowel, final = hangul.split(text[tailAt])
        if initial != 12 or vowel not in (hangul.IH, hangul.YEO):
            start = at + 1
            continue
        if vowel == hangul.YEO:
            base = conjugate(reduced)
            replacement = base[:-1] + hangul.withFinal(base[-1], final) if final else base
        elif final == hangul.BIEUP:
            replacement = polite(reduced)[:-2]
        elif final:
            replacement = reduced[:-1] + hangul.withFinal(reduced[-1], final)
        else:
            replacement = reduced
        return text[:at] + replacement + text[tailAt + 1 :]
    return None


def doublePassiveCandidates(text: str, passives: tuple[str, ...]) -> tuple[Candidate, ...]:
    """이중 피동에서 어지 하나를 뺀 활용 후보."""
    candidates = []
    seen = set()
    for surface in passives:
        voice = decomposePassive(surface)
        if voice is None or voice.reduced is None:
            continue
        candidateText = _reducedPassiveText(text, surface, voice.reduced)
        if candidateText is None or candidateText in seen:
            continue
        seen.add(candidateText)
        candidates.append(Candidate(candidateText, f"`{surface}`의 피동 겹을 하나로 줄인다"))
    return tuple(candidates)
