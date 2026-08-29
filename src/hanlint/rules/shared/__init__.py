"""규칙들이 함께 쓰는 것. 규칙 파일은 여기와 등록부만 import 한다."""

from __future__ import annotations

from .candidates import (
    danglingDeixisCandidates,
    doublePassiveCandidates,
    endingRepeatCandidates,
    longSentenceCandidates,
    nounPileCandidates,
)
from .codeBlocks import CodeBlock, codeBlocksOf
from .dictionaryRule import dictionaryFindings
from .localAntecedent import hasLocalAntecedent
from .repeat import runsOf, shareOf

__all__ = [
    "CodeBlock",
    "codeBlocksOf",
    "danglingDeixisCandidates",
    "dictionaryFindings",
    "doublePassiveCandidates",
    "endingRepeatCandidates",
    "hasLocalAntecedent",
    "longSentenceCandidates",
    "nounPileCandidates",
    "runsOf",
    "shareOf",
]
