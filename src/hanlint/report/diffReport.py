"""두 초안의 지문 차이. 고침이 구조를 바꿨는지 낱말만 바꿨는지 숫자로 보인다. 점수는 없다."""

from __future__ import annotations

from collections import Counter

from ..fingerprint import DocumentPrint
from ..profile.metrics import metricsOf
from ..rules import Finding

METRIC_LABELS = (
    ("sentenceLength", "문장 길이"),
    ("burstiness", "길이 변동"),
    ("commaRatio", "쉼표 비율"),
    ("paragraphSentences", "문단당 문장 수"),
    ("shortParagraphRatio", "짧은 문단 비율"),
)


def delta(before: float, after: float) -> str:
    change = after - before
    sign = "+" if change > 0 else ""
    return f"{before:.2f} → {after:.2f} ({sign}{change:.2f})"


def countDelta(before: int, after: int) -> str:
    change = after - before
    sign = "+" if change > 0 else ""
    return f"{before} → {after} ({sign}{change})" if change else f"{before} → {after}"


def renderDiff(
    beforeDoc: DocumentPrint,
    afterDoc: DocumentPrint,
    beforeFindings: list[Finding],
    afterFindings: list[Finding],
) -> str:
    lines = [
        "짜임        문장 "
        + countDelta(len(beforeDoc.sentences), len(afterDoc.sentences))
        + "  문단 "
        + countDelta(len(beforeDoc.paragraphs), len(afterDoc.paragraphs))
        + "  절 "
        + countDelta(len(beforeDoc.bodySections), len(afterDoc.bodySections))
        + "  어절 "
        + countDelta(beforeDoc.wordCount, afterDoc.wordCount)
    ]
    beforeMetrics = metricsOf(beforeDoc.sentences, beforeDoc.paragraphs)
    afterMetrics = metricsOf(afterDoc.sentences, afterDoc.paragraphs)
    for key, label in METRIC_LABELS:
        if key in beforeMetrics and key in afterMetrics:
            lines.append(f"{label:<11} {delta(beforeMetrics[key], afterMetrics[key])}")
    endings = sorted(
        {key for key in beforeMetrics | afterMetrics if key.startswith("ending:")},
        key=lambda key: -(beforeMetrics.get(key, 0.0) + afterMetrics.get(key, 0.0)),
    )
    mix = ", ".join(
        f"{key.split(':', 1)[1]} {beforeMetrics.get(key, 0.0):.0%} → {afterMetrics.get(key, 0.0):.0%}" for key in endings[:4]
    )
    if mix:
        lines.append(f"종결어미    {mix}")
    beforeErrors = sum(1 for f in beforeFindings if f.severity == "error")
    afterErrors = sum(1 for f in afterFindings if f.severity == "error")
    lines.append(
        "지적        error "
        + countDelta(beforeErrors, afterErrors)
        + "  notice "
        + countDelta(len(beforeFindings) - beforeErrors, len(afterFindings) - afterErrors)
    )
    beforeRules = Counter(f.rule for f in beforeFindings)
    afterRules = Counter(f.rule for f in afterFindings)
    changed = sorted(
        (rule for rule in beforeRules.keys() | afterRules.keys() if beforeRules[rule] != afterRules[rule]),
        key=lambda rule: (afterRules[rule] - beforeRules[rule], rule),
    )
    if changed:
        lines.append("규칙별 변화 " + ", ".join(f"{rule} {beforeRules[rule]} → {afterRules[rule]}" for rule in changed))
    return "\n".join(lines)
