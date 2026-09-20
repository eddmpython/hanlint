"""이음 (joint). 어절 핵 둘이 나란히 온 문장에서 왼쪽에 실제로 붙어 있던 조사를 센다.

`정관 배당` 을 물으면 말뭉치가 `정관은 배당`, `정관에서 배당`, `정관의 배당` 을 문서 수와 함께 답한다. 무엇이 옳은지
고르지 않는다. 그 종류의 글이 그 자리에 무엇을 썼는지만 센다.

왜 있나. 명사 쌓기 (`nounPile`) 와 `의` 사슬 (`euiChain`) 은 고치기가 조사를 하나 넣거나 바꾸는 일이다. 어느 조사인지를
지어내면 그 종류의 글에 없는 꼴이 나온다. 실측: 모델이 자유롭게 고쳐 쓴 문장에서 새로 생긴 어절 결합의 73%가 같은
종류의 말뭉치에 없었고, 명사 쌓기를 풀다 `의` 사슬을 새로 만들어 error 가 2건에서 10건으로 늘었다
(tests/_attempts/usageLift, 2026-09-19). 이음은 그 자리를 말뭉치에 묻는다.

문장 색인 (`sentences`) 위에서만 돈다. 색인은 사용자 기계에만 있다. 없으면 이음도 없다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..analysis.tokenize import stripJosa, words
from .sentences import UsageIndex

JOINT_SAMPLE = 800
"""한 이음을 셀 때 읽을 문장 수 상한. 두 낱말이 함께 든 문장을 일정 간격으로 고르므로 조사의 상대 빈도는 치우치지
않는다. 문서 수는 이 표본 안의 수라 말뭉치 전체보다 작다. 있고 없고가 아니라 그 자리에 어느 조사가 흔한지를 묻는
자리라 표본으로 충분하다. 800 은 흔한 낱말 쌍 (교집합 1만 문장) 에서도 한 이음이 1초 안에 끝나는 크기다."""
MIN_JOINT_DOCUMENTS = 2
"""그 조사를 쓴 문서가 표본에서 몇 편 이상이어야 이음으로 보는가. 한 편은 한 회사의 버릇이다."""


@dataclass(frozen=True)
class Joint:
    particle: str
    """왼쪽 어절에 붙어 있던 조사. 빈 문자열이면 조사 없이 붙여 썼다는 뜻이다 (쌓은 꼴)."""
    documents: int
    """표본 안에서 그렇게 쓴 문서 수."""


def jointParticles(index: UsageIndex, left: str, right: str, sample: int = JOINT_SAMPLE) -> tuple[Joint, ...]:
    """두 어절 핵이 나란히 온 자리의 조사를 문서 수 내림차순으로. 빈 조사도 넣는다 (쌓은 꼴의 근거다)."""
    leftFound, rightFound = index.lookup(left), index.lookup(right)
    if not leftFound or not rightFound:
        return ()
    first = index.postingsAt(leftFound[1], leftFound[2])
    second = index.postingsAt(rightFound[1], rightFound[2])
    if len(first) > len(second):
        first, second = second, first
    other = {sentenceId for sentenceId, _ in second}
    shared = [sentenceId for sentenceId, _ in first if sentenceId in other]
    if not shared:
        return ()
    stride = max(1, len(shared) // sample)
    tally: dict[str, set[str]] = {}
    for sentenceId in shared[::stride][:sample]:
        _, source, text = index.sentence(sentenceId)
        found = words(text)
        for position in range(len(found) - 1):
            before, after = found[position], found[position + 1]
            if before.endsClause or before.particle or after.particle:
                continue
            if stripJosa(before.core) != left or stripJosa(after.core) != right:
                continue
            tally.setdefault(before.core[len(left) :], set()).add(source)
    ranked = sorted(tally.items(), key=lambda item: (-len(item[1]), item[0]))
    return tuple(Joint(particle, len(sources)) for particle, sources in ranked)


class Joints:
    """색인에 이음을 묻고 답을 기억한다. 한 글에서 같은 이음을 여러 지적이 묻는다."""

    def __init__(self, index: UsageIndex, sample: int = JOINT_SAMPLE, minimum: int = MIN_JOINT_DOCUMENTS) -> None:
        self.index = index
        self.sample = sample
        self.minimum = minimum
        self.queries = 0
        """색인을 실제로 읽은 횟수. 기억한 답을 다시 쓰면 늘지 않는다."""
        self._known: dict[tuple[str, str], tuple[Joint, ...]] = {}

    def particles(self, left: str, right: str) -> tuple[Joint, ...]:
        """문서 수가 minimum 편 이상인 이음. 빈 조사도 그대로 준다.

        빈 조사의 뜻은 쓰는 쪽에서 갈린다. 명사 쌓기에서는 원문이 이미 그 꼴이라 고침이 아니고, `의` 사슬에서는
        `의` 를 빼는 고침이다 (`이사회의 결의` -> `이사회 결의`). 여기서 거르면 그 고침이 사라진다.
        """
        key = (left, right)
        if key not in self._known:
            self.queries += 1
            self._known[key] = jointParticles(self.index, left, right, self.sample)
        return tuple(joint for joint in self._known[key] if joint.documents >= self.minimum)
