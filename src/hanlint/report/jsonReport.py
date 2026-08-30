"""기계가 읽는 꼴. 평가 루프의 0층 입력이다. textlint 의 message 와 필드가 대응한다.

지적마다 `exemplar` 를 붙인다. 그 규칙의 고치기 전과 후의 짝이다. 사람이 읽는 꼴은 규칙마다 한 줄로
접지만 기계는 되풀이가 싸다. 본보기 유무의 실제 수정 차이는 tests/_attempts/exemplarLift 에서 따로 잰다.
글쓴이가 승인한 원문 완전 일치 `patch`는 맞는 지적에만 별도로 붙인다.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from ..audit import AuditResult
from ..data import Exemplar, Patch, SurfaceOperation, exemplarFor
from ..fingerprint import DocumentPrint
from ..rules import Finding
from .operationMatch import operationGuidance
from .patchMatch import patchData
from .registerMatch import exemplarInRegister


def findingWithExemplar(
    finding: Finding,
    doc: DocumentPrint | None = None,
    register: str | None = None,
    preset: str | None = None,
    customExemplars: Iterable[Exemplar] = (),
    patches: Iterable[Patch] = (),
) -> dict:
    data = finding.asDict()
    exemplar = exemplarFor(finding.rule, preset, customExemplars)
    if exemplar:
        data["exemplar"] = exemplarInRegister(exemplar, register).asDict()
    selected = patchData(doc, finding, preset, patches)
    if selected:
        data["patch"] = selected
    return data


def renderJson(
    results: dict[str, list[Finding]],
    audits: dict[str, AuditResult] | None = None,
    configLabel: str | None = None,
    registers: dict[str, str] | None = None,
    preset: str | None = None,
    customExemplars: Iterable[Exemplar] = (),
    documents: dict[str, DocumentPrint] | None = None,
    patches: Iterable[Patch] = (),
    operations: Iterable[SurfaceOperation] = (),
    protectedTerms: Iterable[str] = (),
) -> str:
    files = []
    for path, findings in results.items():
        register = registers.get(path) if registers else None
        doc = documents.get(path) if documents else None
        entry: dict = {
            "path": path,
            "findings": [findingWithExemplar(f, doc, register, preset, customExemplars, patches) for f in findings],
        }
        if audits and path in audits:
            entry["audit"] = audits[path].asDict()
        selectedOperations = operationGuidance(doc, findings, preset, operations, patches, protectedTerms)
        if selectedOperations:
            entry["operations"] = selectedOperations
        files.append(entry)
    data: dict = {"version": 1}
    if configLabel is not None:
        data["config"] = configLabel
    data["files"] = files
    return json.dumps(data, ensure_ascii=False, indent=2)
