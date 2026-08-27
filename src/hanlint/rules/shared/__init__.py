"""규칙들이 함께 쓰는 것. 규칙 파일은 여기와 등록부만 import 한다."""

from __future__ import annotations

from .dictionaryRule import dictionaryFindings
from .runs import runsOf

__all__ = ["dictionaryFindings", "runsOf"]
