"""GitHub Actions 의 워크플로 명령 꼴. PR 에 줄 단위 주석이 붙는다."""

from __future__ import annotations

from ..rules import Finding


def renderGithub(path: str, findings: list[Finding]) -> str:
    lines = []
    for finding in findings:
        level = "error" if finding.severity == "error" else "notice"
        message = f"[{finding.rule}] {finding.why}".replace("\n", " ")
        lines.append(f"::{level} file={path},line={finding.line}::{message}")
    return "\n".join(lines)
