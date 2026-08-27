"""한 줄에 지적 하나. AI 와 스크립트가 읽는 꼴이다. 인용문은 빼고 자리와 규칙과 이유만 둔다."""

from __future__ import annotations

from ..rules import Finding


def renderCompact(path: str, findings: list[Finding]) -> str:
    lines = []
    for finding in findings:
        line = f"{path}:{finding.line} [{finding.rule}] {finding.why}"
        if finding.fix:
            line += f"  고친 뒤: {finding.fix}"
        lines.append(line)
    return "\n".join(lines)
