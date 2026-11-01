"""사전과 단어 목록. 단어 목록을 코드 안에 두지 않고 이 폴더의 파일에 둔다. load.py가 읽는다."""

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
from .prose import proseGuide, proseSections

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
    "proseGuide",
    "proseSections",
    "termsIn",
    "vocabularyEntries",
    "vocabularyMetadata",
]
