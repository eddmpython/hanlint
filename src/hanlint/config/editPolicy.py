"""사람이 정한 사실 표현과 규칙별 수정 예산의 닫힌 계약."""

from __future__ import annotations


def checkedEditPolicy(value: object) -> dict[str, dict[str, int]]:
    if not isinstance(value, dict):
        raise ValueError("editPolicy must be an object")
    result = {}
    for rule, limits in value.items():
        if not isinstance(rule, str) or not rule or rule != rule.strip():
            raise ValueError("editPolicy requires rule names")
        if not isinstance(limits, dict) or set(limits) != {"maxChars", "maxLines"}:
            raise ValueError("editPolicy requires maxChars and maxLines")
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in limits.values()):
            raise ValueError("editPolicy limits must be positive integers")
        result[rule] = dict(sorted(limits.items()))
    return dict(sorted(result.items()))
