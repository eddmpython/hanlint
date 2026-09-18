"""사람이 읽는 지적 목록. `파일:줄` 로 시작해 편집기가 바로 연다.

끝에 본보기를 붙인다. 지적은 무엇이 틀렸는지 말하고 본보기는 무엇이 맞는지 보인다. 지적마다 붙이면
같은 줄이 스무 번 나오므로 그 글에 나온 규칙마다 한 짝씩만 낸다.

전과 후를 제 줄에 둔다. 한 줄에 이어 붙였더니 53개 본보기 가운데 23개에서 **답인 `후` 가 잘렸다.**
잘린 짝이 있으면 전문이 어디 있는지 (`hanlint explain`) 머리줄이 한 번 알린다.

확인할 자리 (notice) 는 기본으로 접는다. 규칙마다 개수와 줄 번호 한 줄이다. 실측: README 를 검사할 때마다 같은
확인 12개 (endingRepeat, outsideProfile) 가 오류와 같은 무게로 나와 눈이 무뎌졌다 (2026-09-18). `--notices` 가 편다.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..data import Exemplar, exemplarFor
from ..rules import Finding
from .registerMatch import exemplarInRegister


def exemplarLines(
    findings: list[Finding],
    register: str | None = None,
    preset: str | None = None,
    customExemplars: Iterable[Exemplar] = (),
) -> list[str]:
    """그 글에 나온 규칙의 본보기. 이름 순이고 규칙 하나에 세 줄이다."""
    lines: list[str] = []
    cut = False
    for name in sorted({f.rule for f in findings}):
        exemplar = exemplarFor(name, preset, customExemplars)
        if not exemplar:
            continue
        exemplar = exemplarInRegister(exemplar, register)
        before, after = exemplar.twoLines
        cut = cut or exemplar.shortened
        lines.extend([f"  [{name}]", f"    전  {before}", f"    후  {after}"])
    if not lines:
        return []
    head = "본보기 (고치기 전, 고친 뒤)"
    return [f"{head}. 잘린 것은 hanlint explain <규칙>" if cut else head, *lines]


def candidateLines(findings: list[Finding]) -> list[str]:
    """본보기 아래에 붙이는 선택지. 지적 자리별이며 순위는 없다."""
    chosen = [finding for finding in findings if finding.candidates]
    if not chosen:
        return []
    lines = ["후보 (기계가 고르지 않음)"]
    for finding in chosen:
        lines.append(f"  {finding.line}줄 [{finding.rule}]")
        for candidate in finding.candidates:
            lines.append(f"    - {candidate.text} ({candidate.why})")
    return lines


def noticeLines(notices: list[Finding]) -> list[str]:
    """접은 확인할 자리. 규칙마다 개수와 줄 번호 한 줄, 규칙은 이름 순이다."""
    byRule: dict[str, list[int]] = {}
    for finding in notices:
        byRule.setdefault(finding.rule, []).append(finding.line)
    lines = [f"확인할 자리 {len(notices)} (접음. 다 보려면 --notices)"]
    for rule in sorted(byRule):
        numbers = sorted(set(byRule[rule]))
        lines.append(f"  {rule} {len(byRule[rule])}  {', '.join(str(n) for n in numbers)}줄")
    return lines


def renderText(
    path: str,
    findings: list[Finding],
    register: str | None = None,
    preset: str | None = None,
    customExemplars: Iterable[Exemplar] = (),
    unfoldNotices: bool = False,
) -> str:
    if not findings:
        return f"{path}  집은 자리 없음"
    errors = sum(1 for f in findings if f.severity == "error")
    notices = len(findings) - errors
    summary = f"{path}  집은 자리 {errors}" + (f", 확인할 자리 {notices}" if notices else "")
    lines = [summary, ""]
    folded = [f for f in findings if f.severity == "notice"] if not unfoldNotices else []
    shown = [f for f in findings if unfoldNotices or f.severity == "error"]
    for finding in shown:
        tag = f"[{finding.rule}]" + (" 확인" if finding.severity == "notice" else "")
        lines.append(f"{path}:{finding.line}  {tag}")
        lines.append(f"  {finding.quote}")
        lines.append(f"  {finding.why}")
        if finding.fix:
            lines.append(f"  고친 뒤: {finding.fix}")
        lines.append("")
    if folded:
        lines.extend([*noticeLines(folded), ""])
    lines.extend(exemplarLines(shown, register, preset, customExemplars))
    candidates = candidateLines(shown)
    if candidates:
        lines.extend(["", *candidates])
    return "\n".join(lines).rstrip("\n")
