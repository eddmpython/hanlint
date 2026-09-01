"""설정 층. 임계 기본값의 정본은 settings.py 이고 loadConfig.py 가 파일에서 읽는다."""

from __future__ import annotations

from .loadConfig import loadConfig
from .readerContract import CONTRACT_VERSION, Contract, loadContract
from .settings import DEFAULT_PRESET, PRESET_NAMES, PRESETS, PROFILE_OF, Config
from .writingBrief import (
    BRIEF_VERSION,
    EVIDENCE_BRIEF_VERSION,
    REVIEW_STATUSES,
    AtomicFact,
    EvidenceRecord,
    WritingBrief,
    loadWritingBrief,
    numberValues,
)

__all__ = [
    "BRIEF_VERSION",
    "CONTRACT_VERSION",
    "DEFAULT_PRESET",
    "EVIDENCE_BRIEF_VERSION",
    "PRESETS",
    "PRESET_NAMES",
    "PROFILE_OF",
    "AtomicFact",
    "EvidenceRecord",
    "Config",
    "Contract",
    "WritingBrief",
    "REVIEW_STATUSES",
    "loadConfig",
    "loadContract",
    "loadWritingBrief",
    "numberValues",
]
