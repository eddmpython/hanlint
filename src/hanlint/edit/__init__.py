"""고치기 층. 지적의 fragment 를 원문에서 찾아 replacement 로 바꾼다. 확실한 자리만 바꾸고 나머지는 이유와 함께 남긴다."""

from __future__ import annotations

from .applyFixes import FixResult, applyFixes

__all__ = ["FixResult", "applyFixes"]
