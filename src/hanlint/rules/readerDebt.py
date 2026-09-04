"""독자 부채는 새 판정이 아니라 reader 기제 Finding을 사람이 읽는 이름으로 묶은 것이다."""

from __future__ import annotations

from collections.abc import Iterable

from .finding import Finding
from .registry import ruleMechanism


def readerDebts(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """앞에서 받은 정보로 지금 해결하지 못한 요구만 원래 Finding 순서로 돌려준다."""
    return tuple(finding for finding in findings if ruleMechanism(finding.rule) == "reader")


__all__ = ["readerDebts"]
