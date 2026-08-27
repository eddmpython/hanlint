"""연속 구간 찾기. 같은 값이 이어지는 자리를 (시작 위치, 길이, 값) 으로 준다."""

from __future__ import annotations

from collections.abc import Hashable, Sequence


def runsOf(values: Sequence[Hashable], minLength: int) -> list[tuple[int, int, Hashable]]:
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
