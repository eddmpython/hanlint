"""두 초안의 일대일 문장 고침에서 승인할 표면 치환 후보를 찾는다."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..data import operationFromApproval
from ..fingerprint import DocumentPrint, sourceSentenceTexts
from .edits import changedSentencePairs


@dataclass(frozen=True)
class OperationEvidence:
    """표면 치환 하나를 실제로 수행한 원문과 수정본."""

    sourceBefore: str
    sourceAfter: str
    beforeLine: int
    afterLine: int

    def asDict(self) -> dict:
        return {
            "sourceBefore": self.sourceBefore,
            "sourceAfter": self.sourceAfter,
            "beforeLine": self.beforeLine,
            "afterLine": self.afterLine,
        }


@dataclass(frozen=True)
class LearnedOperation:
    """같은 문서 짝에서 반복 증거를 합친 표면 치환 후보."""

    before: str
    after: str
    evidence: tuple[OperationEvidence, ...]
    presets: tuple[str, ...] = ()

    def asDict(self) -> dict:
        data = {
            "kind": "surfaceSubstitution",
            "before": self.before,
            "after": self.after,
            "evidenceCount": len(self.evidence),
            "evidence": [item.asDict() for item in self.evidence],
            "guards": {
                "maximumCharacters": 32,
                "maximumSurfaceEditDistance": 1,
                "protectedFacts": True,
                "uniqueWordBoundary": True,
            },
        }
        if self.presets:
            data["presets"] = list(self.presets)
        return data


def learnOperations(
    beforeDoc: DocumentPrint,
    afterDoc: DocumentPrint,
    preset: str | None = None,
    protectedTerms: Iterable[str] = (),
) -> tuple[LearnedOperation, ...]:
    """일대일 문장 고침만 보고 뜻을 추측하지 않는 표면 치환 후보를 만든다."""
    pairs = changedSentencePairs(beforeDoc.sentences, afterDoc.sentences)
    rawBefore = sourceSentenceTexts(beforeDoc)
    rawAfter = sourceSentenceTexts(afterDoc)
    beforeByIndex = {sentence.index: sentence for sentence in beforeDoc.sentences}
    grouped: dict[tuple[str, str], list[OperationEvidence]] = {}
    presets = (preset,) if preset else ()
    for beforeIndex, afterSentences in pairs.items():
        if len(afterSentences) != 1:
            continue
        beforeSentence = beforeByIndex.get(beforeIndex)
        afterSentence = afterSentences[0]
        if beforeSentence is None:
            continue
        sourceBefore = rawBefore.get(beforeIndex, beforeSentence.text).strip()
        sourceAfter = rawAfter.get(afterSentence.index, afterSentence.text).strip()
        operation = operationFromApproval(sourceBefore, sourceAfter, presets, protectedTerms)
        if operation is None:
            continue
        evidence = OperationEvidence(sourceBefore, sourceAfter, beforeSentence.line, afterSentence.line)
        grouped.setdefault((operation.before, operation.after), []).append(evidence)
    return tuple(LearnedOperation(before, after, tuple(evidence), presets) for (before, after), evidence in grouped.items())
