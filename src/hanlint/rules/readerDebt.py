"""독자가 막힐 곳. 새로 판정하지 않고, reader 방법을 쓰는 규칙의 지적을 사람이 읽을 이름으로 묶는다."""

from __future__ import annotations

from collections.abc import Iterable

from .finding import Finding
from .registry import ruleMechanism


def readerDebts(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """앞에서 읽은 내용만으로 지금 이해할 수 없는 곳의 지적만 원래 순서대로 돌려준다."""
    return tuple(finding for finding in findings if ruleMechanism(finding.rule) == "reader")


__all__ = ["readerDebts"]
