"""선택한 규칙의 Finding 줄과 원문 변경 창을 대조한다."""

from __future__ import annotations

from ..config import Patch
from ..rules import Finding


def editIssues(text: str, patch: Patch, findings: tuple[Finding, ...], policy: dict) -> tuple[tuple[str, str], ...]:
    if not policy:
        return ()
    limits = policy.get(patch.reason)
    if limits is None:
        return (("editPolicy", "reason has no edit budget"),)
    before, after = patch.before, patch.after
    prefix = 0
    while prefix < min(len(before), len(after)) and before[prefix] == after[prefix]:
        prefix += 1
    suffix = 0
    while suffix < min(len(before), len(after)) - prefix and before[-1 - suffix] == after[-1 - suffix]:
        suffix += 1
    changedBefore = before[prefix : len(before) - suffix if suffix else len(before)]
    changedAfter = after[prefix : len(after) - suffix if suffix else len(after)]
    start = text.index(before) + prefix
    firstLine = text.count("\n", 0, start) + 1
    lastLine = firstLine + changedBefore.count("\n")
    issues = []
    if not any(f.rule == patch.reason and firstLine <= f.line <= lastLine for f in findings):
        issues.append(("editPolicy", "changed range does not contain the Finding line"))
    if max(len(changedBefore), len(changedAfter)) > limits["maxChars"]:
        issues.append(("editPolicy", "changed range exceeds maxChars"))
    if max(changedBefore.count("\n"), changedAfter.count("\n")) + 1 > limits["maxLines"]:
        issues.append(("editPolicy", "changed range exceeds maxLines"))
    return tuple(issues)
