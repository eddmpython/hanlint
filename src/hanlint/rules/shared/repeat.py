"""반복 기제. 같은 모양이 창 안에서 이어지거나 (runsOf) 한 모양이 창을 채우는 (shareOf) 자리를 센다.

repeat 기제의 규칙은 무엇을 모양 (열쇠) 으로 볼지와 창과 임계만 선언하고 셈은 여기서 한다. endingRepeat 은
종결어미, connectorRepeat 은 문두 접속부사, paraFragment 는 짧은 문단, headingUniform 은 H2 끝 글자를 열쇠로
준다. 같은 셈을 규칙마다 따로 들면 규칙이 늘 때마다 셈도 는다. 셈은 하나고 열쇠만 다르다.
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
