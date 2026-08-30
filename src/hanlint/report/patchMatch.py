"""현재 지적과 지문을 승인 패치의 선택 조건에 맞댄다."""

from __future__ import annotations

from collections.abc import Iterable

from ..data import Patch, patchFor
from ..fingerprint import DocumentPrint, readerKind, sourceSentenceText
from ..rules import Finding
from ..rules.finding import SENTENCE


def selectedPatch(
    doc: DocumentPrint | None,
    finding: Finding,
    preset: str | None,
    patches: Iterable[Patch],
) -> Patch | None:
    """승인 원문과 현재 독자 상태까지 계산해 유일하게 맞는 패치를 고른다."""
    patches = tuple(patches)
    if not patches or doc is None or finding.scope != SENTENCE or finding.at < 0 or finding.at >= len(doc.sentences):
        return None
    sentence = doc.sentences[finding.at]
    sourceText = sourceSentenceText(doc, sentence)
    if sourceText is None:
        return None
    state = doc.reader.beforeSentence[finding.at]
    return patchFor(
        finding.rule,
        preset,
        sourceText,
        sentence.text,
        finding.localCue,
        readerKind(sentence, state),
        patches,
    )


def patchData(doc: DocumentPrint | None, finding: Finding, preset: str | None, patches: Iterable[Patch]) -> dict | None:
    patch = selectedPatch(doc, finding, preset, patches)
    return patch.asDict(preset) if patch and preset else None
