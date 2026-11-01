"""사람이 정한 사실 표현과 규칙별 수정 예산의 닫힌 계약."""

from __future__ import annotations


def checkedEditPolicy(value: object) -> dict[str, dict[str, int]]:
    if not isinstance(value, dict):
        raise ValueError("editPolicy는 객체여야 한다")
    result = {}
    for rule, limits in value.items():
        if not isinstance(rule, str) or not rule or rule != rule.strip():
            raise ValueError("editPolicy에는 규칙 이름이 있어야 한다")
        if not isinstance(limits, dict) or set(limits) != {"maxChars", "maxLines"}:
            raise ValueError("editPolicy의 규칙마다 maxChars와 maxLines가 있어야 한다")
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in limits.values()):
            raise ValueError("editPolicy의 한도는 양의 정수여야 한다")
        result[rule] = dict(sorted(limits.items()))
    return dict(sorted(result.items()))
