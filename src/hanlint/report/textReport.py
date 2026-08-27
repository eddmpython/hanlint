"""사람이 읽는 지적 목록. `파일:줄` 로 시작해 편집기가 바로 연다.

끝에 본보기를 붙인다. 지적은 무엇이 틀렸는지 말하고 본보기는 무엇이 맞는지 보인다. 지적마다 붙이면
같은 줄이 스무 번 나오므로 그 글에 나온 규칙마다 한 줄씩만 낸다.
"""

from __future__ import annotations

from ..data import exemplarFor
from ..rules import Finding


def exemplarLines(findings: list[Finding]) -> list[str]:
    """그 글에 나온 규칙의 본보기. 이름 순이고 규칙 하나에 한 줄이다."""
    lines = []
    for name in sorted({f.rule for f in findings}):
        exemplar = exemplarFor(name)
        if exemplar:
            lines.append(f"  [{name}] {exemplar.oneLine}")
    return ["본보기 (고치기 전 -> 고친 뒤)", *lines] if lines else []


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
    lines.extend(exemplarLines(findings))
    return "\n".join(lines).rstrip("\n")
