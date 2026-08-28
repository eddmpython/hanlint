"""문체. 글이 합니다체인지 한다체인지 해요체인지를 판별하고, 글을 다른 문체로 바꾼다.

**왜 있는가.** 본보기 53개와 문형 10개가 전부 합니다체다. 한다체 문서를 검사하면 남의 말투로 고치라고
보여 준다. 기준 말뭉치 390편은 한다체 340편, 합니다체 45편, 해요체 1편, 섞임 3편, 없음 1편이었다.
보여 주는 쪽이 글에 맞춰야 한다.

**판별은 평서문만 센다.** 물음 (`생겼을까요`) 과 명령 (`보세요`) 은 합니다체 글에서도 그 꼴로 쓰이므로
문체를 가르지 못한다. 평서문 가운데 가장 많은 것이 그 글의 문체이고, 그 비율이 임계 아래면 `섞임` 이다.
우세 비율 0.7은 말뭉치의 실제 혼합 기사 0.625와 일관된 에세이 하위 5% 0.7576 사이에서 정했다.

**변환은 문장 끝 서술어만 바꾼다.** 문장 안의 인용문, 코드, 제목, 표는 건드리지 않는다. 서술어를 못 푼
문장은 그대로 두고 그 수를 센다. 본보기와 문형의 게이트는 그 수가 0 이어야 통과다.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from . import hangul
from .ending import HAEYO, HANDA, HAPNIDA, REGISTERS, parsePredicate, render

MIXED = "섞임"
NONE = "없음"

SENTENCE_END = re.compile(r"(?P<word>[가-힣]+)(?P<punct>[.?!]+)(?P<close>[\"”’)\]]*)(?=\s|$)")
"""문장 끝. 한글 어절 뒤에 종결 부호, 그 뒤에 닫는 따옴표나 괄호가 올 수 있다."""
WORD_BEFORE = re.compile(r"(\S+)\s+$")
SKIP_LINE = re.compile(r"^\s*(#|\||```|---)")
"""제목, 표, 펜스, frontmatter 경계는 서술어가 없다."""
TEMPLATE_WORD = re.compile(r"\{(?P<word>[가-힣]+)\}")
BARE_LINE_END = re.compile(r"(?P<word>[가-힣]+)$", re.MULTILINE)


def registerOfWord(word: str) -> str | None:
    """평서문 끝 어절의 문체. 합니다, 한다, 해요 가운데 하나이거나 None.

    `니다` 로 끝난다고 다 합니다체가 아니다. `아니다` 는 한다체다. `습니다` 이거나 `니` 앞 음절에 ㅂ 받침이
    있어야 합니다체다 (봅니다, 입니다).
    """
    if word.endswith("습니다") or (word.endswith("니다") and len(word) >= 3 and hangul.finalOf(word[-3]) == hangul.BIEUP):
        return HAPNIDA
    if word.endswith("요"):
        return HAEYO
    if word.endswith("다"):
        return HANDA
    return None


def lastWord(text: str) -> str:
    """문장의 마지막 한글 어절. 뒤의 부호는 뗀다."""
    body = text.rstrip().rstrip('.?!"”’)]」』')
    match = re.search(r"([가-힣]+)$", body)
    return match.group(1) if match else ""


def documentRegister(words: list[str], minShare: float) -> tuple[str, float]:
    """평서문 끝 어절들에서 글의 문체와 그 비율. 하나도 없으면 (없음, 0)."""
    counted = Counter(r for r in (registerOfWord(w) for w in words) if r)
    total = sum(counted.values())
    if not total:
        return NONE, 0.0
    register, count = max(counted.items(), key=lambda kv: (kv[1], REGISTERS.index(kv[0])))
    share = count / total
    return (register if share >= minShare else MIXED), share


@dataclass(frozen=True)
class Conversion:
    text: str
    converted: int
    """바꾼 서술어 수."""
    skipped: int
    """못 풀어서 그대로 둔 서술어 수. 본보기와 문형은 이것이 0 이어야 한다."""


def convertLine(line: str, target: str) -> tuple[str, int, int]:
    converted = skipped = 0

    def swap(match: re.Match[str]) -> str:
        nonlocal converted, skipped
        word, punct, close = match.group("word"), match.group("punct"), match.group("close")
        if registerOfWord(word) is None:
            return match.group(0)
        before = WORD_BEFORE.search(line[: match.start()])
        previous = before.group(1) if before else None
        predicate = parsePredicate(word, previous)
        if predicate is None:
            skipped += 1
            return match.group(0)
        converted += 1
        return render(predicate, target) + punct + close

    return SENTENCE_END.sub(swap, line), converted, skipped


def convertRegister(text: str, target: str) -> Conversion:
    """글의 서술어를 그 문체로 바꾼다. 코드 펜스 안과 제목과 표는 그대로다."""
    if target not in REGISTERS:
        raise ValueError(f"모르는 문체: {target}. {', '.join(REGISTERS)} 가운데 하나다")
    out: list[str] = []
    converted = skipped = 0
    inFence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inFence = not inFence
            out.append(line)
            continue
        if inFence or SKIP_LINE.match(line):
            out.append(line)
            continue
        changed, c, s = convertLine(line, target)
        out.append(changed)
        converted += c
        skipped += s
    return Conversion("\n".join(out), converted, skipped)


def convertTemplate(text: str, target: str) -> Conversion:
    """문장과 문형의 활용형을 바꾼다. 문형의 `{생깁니다}` 같은 활용 자리까지 본다.

    중괄호 안 명사가 대부분이므로 문체를 가진 낱말만 서술어로 푼다. 못 푼 문체 낱말은 skipped에 센다.
    """
    result = convertRegister(text, target)
    converted = result.converted
    skipped = result.skipped

    def swapBare(match: re.Match[str]) -> str:
        nonlocal converted, skipped
        word = match.group("word")
        if registerOfWord(word) is None:
            return word
        lineStart = result.text.rfind("\n", 0, match.start()) + 1
        before = WORD_BEFORE.search(result.text[lineStart : match.start()])
        previous = before.group(1) if before else None
        predicate = parsePredicate(word, previous)
        if predicate is None:
            skipped += 1
            return word
        converted += 1
        return render(predicate, target)

    bare = BARE_LINE_END.sub(swapBare, result.text)

    def swap(match: re.Match[str]) -> str:
        nonlocal converted, skipped
        word = match.group("word")
        if registerOfWord(word) is None:
            return match.group(0)
        predicate = parsePredicate(word)
        if predicate is None:
            skipped += 1
            return match.group(0)
        converted += 1
        return "{" + render(predicate, target) + "}"

    return Conversion(TEMPLATE_WORD.sub(swap, bare), converted, skipped)
