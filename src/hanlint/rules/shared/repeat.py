"""반복을 세는 방법. 같은 값이 이어지는 구간(runsOf)과 한 값이 차지하는 비율(shareOf)을 센다.

repeat 방법을 쓰는 규칙은 무엇을 값(열쇠)으로 볼지와 기준값만 정하고 세는 일은 여기서 한다. endingRepeat은
종결어미, connectorRepeat은 문장 첫머리 접속부사, paraFragment는 짧은 문단, headingUniform은 H2 끝 글자를 열쇠로
준다. 같은 셈을 규칙마다 따로 두면 규칙이 늘 때마다 셈도 는다. 셈은 하나고 열쇠만 다르다.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence


def runsOf(values: Sequence[Hashable], minLength: int) -> list[tuple[int, int, Hashable]]:
    """같은 값이 minLength 개 이상 이어지는 구간을 (시작 위치, 길이, 값) 으로 준다."""
    runs: list[tuple[int, int, Hashable]] = []
    start = 0
    while start < len(values):
        end = start
        while end + 1 < len(values) and values[end + 1] == values[start]:
            end += 1
        length = end - start + 1
        if length >= minLength:
            runs.append((start, length, values[start]))
        start = end + 1
    return runs


def shareOf(values: Sequence[Hashable]) -> tuple[Hashable, int, int]:
    """가장 많은 값과 그 수와 전체 수. 같은 수면 먼저 나온 값이 이긴다. 빈 열이면 (None, 0, 0)."""
    counts: dict[Hashable, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    best: Hashable = None
    count = 0
    for value, seen in counts.items():
        if seen > count:
            best, count = value, seen
    return best, count, len(values)
