"""고치기 층. 지적의 fragment 를 원문에서 찾아 replacement 로 바꾸고, 말뭉치가 뒷받침하는 고침 후보를 채운다."""

from __future__ import annotations

from .applyFixes import FixResult, applyFixes
from .usageCandidates import MAX_CANDIDATES, candidatesFor, usageCandidates

__all__ = ["MAX_CANDIDATES", "FixResult", "applyFixes", "candidatesFor", "usageCandidates"]
