"""글쓴이의 실제 고침에서 승인할, 원문이 같을 때 그대로 쓰는 패치와 글자 바꾸기 후보를 찾는 부분."""

from __future__ import annotations

from .edits import LearnedExemplar, learnExemplars
from .operations import LearnedOperation, OperationEvidence, learnOperations

__all__ = ["LearnedExemplar", "LearnedOperation", "OperationEvidence", "learnExemplars", "learnOperations"]
