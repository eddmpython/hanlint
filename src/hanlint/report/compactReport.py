"""한 줄에 지적 하나. AI 와 스크립트가 읽는 꼴이다. 인용문은 빼고 자리와 규칙과 이유만 둔다.

**한 줄은 계약이다.** 실측: 원문에서 두 줄에 걸친 문장의 고침 제안이 그 줄바꿈을 그대로 들고 나와
지적 하나가 두 줄이 됐다. 둘째 줄에는 파일도 줄 번호도 규칙 이름도 없어서 `grep` 이 반토막을 냈고
줄을 세면 지적 수와 안 맞았다. 스크립트와 기계가 읽는 꼴이라 이 자리에서 눕힌다.
"""

from __future__ import annotations

from ..rules import Finding


def flat(text: str) -> str:
    """줄바꿈과 이어진 공백을 하나로 눕힌다."""
    return " ".join(text.split())


def renderCompact(path: str, findings: list[Finding]) -> str:
    lines = []
    for finding in findings:
        line = f"{path}:{finding.line} [{finding.rule}] {flat(finding.why)}"
        if finding.fix:
            line += f"  고친 뒤: {flat(finding.fix)}"
        lines.append(line)
    return "\n".join(lines)
