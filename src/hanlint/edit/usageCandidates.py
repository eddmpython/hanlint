"""말뭉치가 뒷받침하는 고침 후보를 지적에 채운다. 닫힌 목록이고, 짓지 않고 고른다.

왜 이 통로인가. 같은 용례를 프롬프트에 얹는 방식은 네 번 재서 네 번 다 효과가 없었다 (300쌍, 두 모델, 세 조건,
부호검정 p 1.0000. tests/_attempts/usageLift). 모델이 문장을 자유롭게 다시 쓰면 말뭉치에 없는 결합을 만들고
(새 결합의 73%), 명사 쌓기를 풀다 `의` 사슬을 새로 만들었다 (새 error 2건 -> 10건). 통로를 바꾼다. 무엇을 쓸지를
묻지 않고 **말뭉치가 그 자리에 실제로 쓴 것 가운데 무엇을 고를지**를 묻는다.

만드는 법 (두 단계, 둘 다 결정적이다).
1. 자리와 조사는 `usage.joints` 가 말뭉치에서 센다. 지어낸 조사는 없다.
2. 후보마다 hanlint 를 다시 돌린다. 겨눈 규칙이 풀리고 error 가 늘지 않는 것만 남는다.

순위도 점수도 매기지 않는다. 문서 수는 근거지 등수가 아니다. 어느 후보가 뜻에 맞는지는 고르는 쪽 (사람이나 LLM) 이
정한다. 뜻을 이해해야 갈리는 자리를 여기서 정하지 않는 것이 hanlint 의 경계다.

문장 색인이 있어야 돈다. 색인은 사용자 기계에만 있고 `hanlint usage build` 가 만든다. 없으면 빈 목록이다.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ..analysis import genitiveSpans, nounRuns, stripJosa, words, wordSpans
from ..analysis.grammar import fitJosa
from ..config import Config
from ..document import parseMarkdown
from ..fingerprint import buildFingerprint
from ..rules import Candidate, Finding, runAll
from ..usage import Joint, Joints, UsageIndex, defaultUsageRoot, loadIndex, usageKindOf

JOINT_RULES = ("nounPile", "euiChain")
"""이음으로 고칠 수 있는 규칙. 둘 다 고치기가 조사 하나를 넣거나 바꾸는 일이다."""
MAX_CANDIDATES = 6
"""한 지적에 실을 후보 수 상한. 고르는 쪽이 한눈에 읽을 크기다. 등수가 아니라 근거 문서 수 내림차순의 앞부분이다."""
MAX_SLOTS = 10
"""한 문장에서 볼 자리 수 상한. 근거가 많은 차례로 앞에서 자른다.

자리가 이보다 많은 문장은 조사를 끼워 고칠 문장이 아니라 다시 쓸 문장이다. 상한이 없으면 사업보고서의 긴 한 문장
(`의` 자리 수십 개) 이 후보 수백 개를 만들고, 후보마다 검사를 다시 도느라 글 하나가 분 단위로 늘어진다."""


@dataclass(frozen=True)
class Slot:
    """고칠 수 있는 한 자리. 말뭉치가 그 자리에 쓴 조사 하나가 자리 하나다."""

    at: int
    stop: int
    """[at, stop) 을 particle 로 바꾼다. 넣기만 할 때는 둘이 같다."""
    particle: str
    documents: int
    """그 조사를 쓴 글의 수. 근거지 등수가 아니다."""
    why: str


def applyEdits(text: str, slots: list[Slot]) -> str:
    """자리들을 뒤에서부터 적용한다. 앞을 먼저 고치면 뒤 자리가 밀린다."""
    for slot in sorted(slots, key=lambda one: -one.at):
        text = text[: slot.at] + slot.particle + text[slot.stop :]
    return text


def jointWhy(left: str, joint: Joint, right: str) -> str:
    """후보의 근거 한 줄. 자기 도구가 검사하는 글이라 조사를 받침에 맞춘다."""
    shown = f"{left}{joint.particle} {right}"
    return f"`{shown}`{fitJosa(shown, '로')} 쓴 글 {joint.documents}편"


def chainBoundaries(text: str, minimum: int) -> list[int]:
    """임계 이상인 명사 연쇄 안의 어절 경계. words() 차례의 왼쪽 어절 index 다."""
    piles = {tuple(chain) for chain, length in nounRuns(text) if length >= minimum}
    if not piles:
        return []
    cores = [word.core for word in words(text)]
    places: set[int] = set()
    for chain in piles:
        for start in range(len(cores) - len(chain) + 1):
            if cores[start : start + len(chain)] == list(chain):
                places.update(range(start, start + len(chain) - 1))
    return sorted(places)


def nounPileSlots(text: str, joints: Joints, minimum: int) -> list[Slot]:
    """명사 쌓기 경계마다 넣을 수 있는 조사. 말뭉치가 붙여서만 쓰는 경계는 자리가 아니다."""
    spans = wordSpans(text)
    cores = [stripJosa(word.core) for word in words(text)]
    slots: list[Slot] = []
    for position in chainBoundaries(text, minimum):
        left, right = cores[position], cores[position + 1]
        at = spans[position][1]
        for joint in joints.particles(left, right):
            if not joint.particle:
                continue
            slots.append(Slot(at, at, joint.particle, joint.documents, jointWhy(left, joint, right)))
    return slots


def euiChainSlots(text: str, joints: Joints) -> list[Slot]:
    """`의` 자리마다 바꿔 넣을 수 있는 조사. 빈 조사는 `의` 를 빼는 고침이다."""
    spans = wordSpans(text)
    found = words(text)
    cores = [stripJosa(word.core) for word in found]
    starts = {span[0]: position for position, span in enumerate(spans)}
    slots: list[Slot] = []
    for start, end in genitiveSpans(text):
        position = starts.get(start)
        if position is None or position + 1 >= len(found) or not text[start:end].endswith("의"):
            continue
        left, right = cores[position], cores[position + 1]
        for joint in joints.particles(left, right):
            if joint.particle == "의":
                continue
            slots.append(Slot(end - 1, end, joint.particle, joint.documents, jointWhy(left, joint, right)))
    return slots


def slotCandidates(text: str, slots: list[Slot]) -> list[tuple[str, str]]:
    """자리 하나씩 고친 꼴과, 자리 여럿을 함께 고친 꼴.

    하나씩 고친 꼴을 근거가 많은 차례로 먼저 낸다 (같으면 원문에서 앞선 자리). 등수가 아니라 읽는 차례다.
    한 자리만 고쳐서는 안 풀리는 지적이 많아 (`의` 가 넷이면 하나 바꿔도 셋이다) 자리를 쌓은 꼴을 뒤에 붙인다.
    쌓는 쪽은 자리를 원문 차례대로 더할 뿐 조합을 다 펼치지 않고, 자리마다 그 자리에서 근거가 가장 많은 조사를 쓴다.
    """
    made: list[tuple[str, str]] = []
    seen = {text}
    for slot in sorted(slots, key=lambda one: (-one.documents, one.at, one.particle)):
        candidate = applyEdits(text, [slot])
        if candidate not in seen:
            seen.add(candidate)
            made.append((candidate, slot.why))
    best: dict[int, Slot] = {}
    for slot in sorted(slots, key=lambda one: (-one.documents, one.particle)):
        best.setdefault(slot.at, slot)
    ordered = [best[at] for at in sorted(best)]
    for count in range(2, len(ordered) + 1):
        chosen = ordered[:count]
        candidate = applyEdits(text, chosen)
        if candidate not in seen:
            seen.add(candidate)
            made.append((candidate, f"자리 {count}곳을 함께. " + " / ".join(slot.why for slot in chosen)))
    return made


def sentenceTally(text: str, config: Config) -> dict[str, int]:
    """규칙 이름별 지적 수. 한 문장만 넣으므로 문단과 문서 규칙은 돌지 않는다."""
    counts: dict[str, int] = {}
    for finding in runAll(buildFingerprint(parseMarkdown(text), config), config):
        counts[finding.rule] = counts.get(finding.rule, 0) + 1
    return counts


def keeps(candidate: str, rule: str, before: dict[str, int], config: Config) -> bool:
    """겨눈 규칙이 줄고 **다른 어떤 규칙도 늘지 않으면** 남는다. 고치다 새 결함을 만드는 길을 막는 자리다.

    error 총수로 보면 안 된다. 쌓기 하나가 사라지고 `의` 사슬 하나가 생기면 총수가 같아 그대로 남는다.
    그것이 실측에서 새 error 를 2건에서 10건으로 늘린 바로 그 꼴이다 (tests/_attempts/usageLift).
    notice 도 막는다. 지적은 지적이고, 여기서 둘을 갈라 예외를 두기 시작하면 목록이 늘어난다.
    """
    after = sentenceTally(candidate, config)
    if after.get(rule, 0) >= before.get(rule, 0):
        return False
    return all(count <= before.get(name, 0) for name, count in after.items())


def candidatesFor(text: str, rule: str, joints: Joints, config: Config, limit: int = MAX_CANDIDATES) -> tuple[Candidate, ...]:
    """한 문장의 한 규칙에 대한 닫힌 후보 목록. 말뭉치가 뒷받침하고 다시 검사해도 규칙이 풀리는 것만."""
    slots = nounPileSlots(text, joints, config.nounPileMin) if rule == "nounPile" else euiChainSlots(text, joints)
    slots = sorted(slots, key=lambda one: (-one.documents, one.at, one.particle))[:MAX_SLOTS]
    if not slots:
        return ()
    before = sentenceTally(text, config)
    kept = []
    for candidate, why in slotCandidates(text, slots):
        if len(kept) >= limit:
            break
        if keeps(candidate, rule, before, config):
            kept.append(Candidate(candidate, why))
    return tuple(kept)


def usageCandidates(
    text: str,
    config: Config | None = None,
    root: Path | None = None,
    index: UsageIndex | None = None,
    limit: int = MAX_CANDIDATES,
) -> list[Finding]:
    """후보가 붙은 지적만 준다. 색인이 없거나 종류가 정해지지 않았으면 빈 목록이다."""
    config = config or Config()
    if index is None:
        kind = usageKindOf(config)
        index = loadIndex(kind, root or defaultUsageRoot()) if kind else None
    if index is None:
        return []
    joints = Joints(index)
    found: list[Finding] = []
    for finding in runAll(buildFingerprint(parseMarkdown(text), config), config):
        if finding.rule not in JOINT_RULES:
            continue
        made = candidatesFor(finding.quote, finding.rule, joints, config, limit)
        if made:
            found.append(replace(finding, candidates=made))
    return found
