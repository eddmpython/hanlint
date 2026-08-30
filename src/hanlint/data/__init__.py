"""사전과 표지 목록. 코드 안에 낱말 목록을 두지 않고 여기 파일이 정본이다. load.py 가 읽는다."""

from __future__ import annotations

from .exemplars import Exemplar, allExemplars, exemplarFor, exemplars, projectExemplars
from .learningVocabulary import Term, VocabularyEntry, gradesByLexeme, termsIn, vocabularyEntries, vocabularyMetadata
from .load import loadLines, loadPatterns, loadToml
from .patches import READER_KINDS, Patch, flatCue, flatSentence, patchFor, projectPatches
from .patterns import Pattern, patterns, patternsAvoiding

__all__ = [
    "Exemplar",
    "Pattern",
    "Patch",
    "READER_KINDS",
    "Term",
    "VocabularyEntry",
    "allExemplars",
    "exemplarFor",
    "exemplars",
    "gradesByLexeme",
    "loadLines",
    "loadPatterns",
    "loadToml",
    "flatCue",
    "flatSentence",
    "patchFor",
    "patterns",
    "patternsAvoiding",
    "projectExemplars",
    "projectPatches",
    "termsIn",
    "vocabularyEntries",
    "vocabularyMetadata",
]
