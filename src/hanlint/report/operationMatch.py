"""현재 문장에 승인 표면 치환이 안전하게 하나만 적용되는지 계산한다."""

from __future__ import annotations

from collections.abc import Iterable

from ..data import Patch, SurfaceOperation, operationFor
from ..fingerprint import DocumentPrint, sourceSentenceTexts
from ..rules import Finding
from .patchMatch import selectedPatch


def operationGuidance(
    doc: DocumentPrint | None,
    findings: Iterable[Finding],
    preset: str | None,
    operations: Iterable[SurfaceOperation],
    patches: Iterable[Patch] = (),
    protectedTerms: Iterable[str] = (),
) -> list[dict]:
    """확정 fix나 원문 완전 일치 패치가 맡은 문장은 건너뛰고 유일한 표면 치환만 싣는다."""
    operations = tuple(operations)
    findings = tuple(findings)
    patches = tuple(patches)
    if doc is None or not preset or not operations:
        return []
    reserved = {finding.at for finding in findings if finding.at >= 0 and finding.fix is not None}
    reserved.update(
        finding.at for finding in findings if finding.at >= 0 and selectedPatch(doc, finding, preset, patches) is not None
    )
    sourceTexts = sourceSentenceTexts(doc)
    guidance = []
    for sentence in doc.sentences:
        if sentence.index in reserved:
            continue
        sourceText = sourceTexts.get(sentence.index)
        if sourceText is None:
            continue
        applied = operationFor(sourceText, preset, operations, protectedTerms)
        if applied is not None:
            guidance.append({"line": sentence.line, "operation": applied.asDict(preset)})
    return guidance
