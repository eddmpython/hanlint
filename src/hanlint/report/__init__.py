"""출력 층. Finding 과 분석 결과와 지문을 사람과 기계가 읽는 꼴로 낸다."""

from __future__ import annotations

from .auditReport import renderAudit
from .compactReport import renderCompact
from .diffReport import renderDiff
from .fingerprintJson import LAYERS, fingerprintDict, renderFingerprintJson
from .githubReport import renderGithub
from .jsonReport import renderJson
from .mapHtml import renderMapHtml
from .mapText import renderMap
from .registerMatch import exemplarInRegister, patternInRegister, targetRegister
from .textReport import renderText
from .writingPacket import PURPOSES, buildWritingPacket, renderWritingPacket

__all__ = [
    "LAYERS",
    "PURPOSES",
    "buildWritingPacket",
    "fingerprintDict",
    "renderAudit",
    "renderCompact",
    "renderDiff",
    "renderFingerprintJson",
    "renderGithub",
    "renderJson",
    "renderMap",
    "renderMapHtml",
    "renderText",
    "renderWritingPacket",
    "exemplarInRegister",
    "patternInRegister",
    "targetRegister",
]
