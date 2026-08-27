"""규칙 층. 규칙 하나가 파일 하나이고 등록부가 전부 돈다. 규칙은 지문만 읽는다."""

from __future__ import annotations

from .finding import Finding
from .registry import ruleDoc, ruleNames, ruleSummary, runAll

__all__ = ["Finding", "ruleDoc", "ruleNames", "ruleSummary", "runAll"]
