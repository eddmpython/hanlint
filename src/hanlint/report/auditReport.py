"""분석 결과의 터미널 꼴. 지도 아래 분포 숫자가 붙는다."""

from __future__ import annotations

from ..audit import AuditResult
from ..fingerprint import DocumentPrint
from ..rules import Finding
from .mapText import renderMap


def bar(ratio: float, width: int = 20) -> str:
    filled = round(ratio * width)
    return "█" * filled + "·" * (width - filled)


def renderAudit(doc: DocumentPrint, findings: list[Finding], audit: AuditResult, color: bool = False) -> str:
    lines = [renderMap(doc, findings, color), ""]
    rhythm = audit.rhythm
    lines.append(f"문장 길이   평균 {rhythm.mean:.1f} 어절, 표준편차 {rhythm.std:.1f}, 편차/평균 {rhythm.burstiness:.2f}")
    total = max(1, audit.sentenceCount)
    for label, count in rhythm.histogram:
        lines.append(f"  {label:>6} 어절  {bar(count / total)} {count}")
    lines.append(f"문단 길이   두 문장 이하 문단 {audit.shortParagraphRatio:.0%}")
    total = max(1, audit.paragraphCount)
    for label, count in audit.paragraphHistogram:
        lines.append(f"  {label:>6} 문장  {bar(count / total)} {count}")
    lines.append(f"쉼표        쉼표가 있는 문장 {audit.commaRatio:.0%}")
    mix = ", ".join(f"{ending} {ratio:.0%}" for ending, ratio in audit.endingMix[:5])
    lines.append(f"종결어미    {mix}")
    lexicon = audit.lexicon
    lines.append(
        f"어휘        어절 {lexicon.tokens}, 낱말 종류 {lexicon.types}, 종류/어절 {lexicon.typeTokenRatio:.2f}, "
        f"영문 어절 {lexicon.foreignRatio:.0%}"
    )
    if lexicon.topWords:
        lines.append("자주 쓴 말  " + ", ".join(f"{word} {count}" for word, count in lexicon.topWords))
    if audit.connectorMix:
        lines.append("문두 접속사 " + ", ".join(f"{word} {count}" for word, count in audit.connectorMix))
    d = audit.density
    lines.append(
        f"천 어절당   접속사 {d.connectors:.1f}, 지시어 {d.deixis:.1f}, 강조 낱말 {d.emphasis:.1f}, "
        f"헤지 {d.hedges:.1f}, 수치 {d.numbers:.1f}"
    )
    lines.append(f"독자        질문 {audit.questionCount}, 독자 호출 {audit.readerCallCount}")
    if audit.valleys:
        spots = ", ".join(f"{v.line}행" for v in audit.valleys)
        lines.append(f"흐름 골짜기 {spots} (앞 문단과 화제어 겹침 0)")
    lines.append("절          " + "  ".join(f"{s.title[:10]}: 문단 {s.paragraphs} 코드 {s.codeBlocks}" for s in audit.sections))
    lines.append(f"제목 수준   {' '.join(f'H{level}' for level in audit.headingLevels)}")
    return "\n".join(lines)
