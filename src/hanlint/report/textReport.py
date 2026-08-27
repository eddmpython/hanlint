"""사람이 읽는 지적 목록. `파일:줄` 로 시작해 편집기가 바로 연다."""

from __future__ import annotations

from ..rules import Finding


def renderText(path: str, findings: list[Finding]) -> str:
    if not findings:
        return f"{path}  집은 자리 없음"
    errors = sum(1 for f in findings if f.severity == "error")
    notices = len(findings) - errors
    summary = f"{path}  집은 자리 {errors}" + (f", 확인할 자리 {notices}" if notices else "")
    lines = [summary, ""]
    for finding in findings:
        tag = f"[{finding.rule}]" + (" 확인" if finding.severity == "notice" else "")
        lines.append(f"{path}:{finding.line}  {tag}")
        lines.append(f"  {finding.quote}")
        lines.append(f"  {finding.why}")
        if finding.fix:
            lines.append(f"  고친 뒤: {finding.fix}")
        lines.append("")
    return "\n".join(lines).rstrip("\n")
