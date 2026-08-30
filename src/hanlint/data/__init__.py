"""사전과 표지 목록. 코드 안에 낱말 목록을 두지 않고 여기 파일이 정본이다. load.py 가 읽는다."""

from __future__ import annotations

from .exemplars import Exemplar, allExemplars, exemplarFor, exemplars, projectExemplars
from .learningVocabulary import Term, VocabularyEntry, gradesByLexeme, termsIn, vocabularyEntries, vocabularyMetadata
from .load import loadLines, loadPatterns, loadToml
from .operations import (
    AppliedOperation,
    SurfaceOperation,
    applyOperation,
    operationFor,
    operationFromApproval,
    projectOperations,
    protectedTermAtoms,
)
from .patches import READER_KINDS, Patch, flatCue, flatSentence, patchFor, projectPatches
from .patterns import Pattern, patterns, patternsAvoiding

__all__ = [
    "Exemplar",
    "AppliedOperation",
    "Pattern",
    "Patch",
    "SurfaceOperation",
    "READER_KINDS",
    "Term",
    "VocabularyEntry",
    "allExemplars",
    "applyOperation",
    "exemplarFor",
    "exemplars",
    "gradesByLexeme",
    "loadLines",
    "loadPatterns",
    "loadToml",
    "operationFor",
    "operationFromApproval",
    "protectedTermAtoms",
    "flatCue",
    "flatSentence",
    "patchFor",
    "patterns",
    "patternsAvoiding",
    "projectExemplars",
    "projectOperations",
    "projectPatches",
    "termsIn",
    "vocabularyEntries",
    "vocabularyMetadata",
]
