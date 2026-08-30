"""기계가 읽는 꼴. 평가 루프의 0층 입력이다. textlint 의 message 와 필드가 대응한다.

지적마다 `exemplar` 를 붙인다. 그 규칙의 고치기 전과 후의 짝이다. 사람이 읽는 꼴은 규칙마다 한 줄로
접지만 기계는 되풀이가 싸다. 본보기 유무의 실제 수정 차이는 tests/_attempts/exemplarLift 에서 따로 잰다.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from ..audit import AuditResult
from ..data import Exemplar, exemplarFor
from ..rules import Finding
from .registerMatch import exemplarInRegister


def findingWithExemplar(
    finding: Finding,
    register: str | None = None,
    preset: str | None = None,
    customExemplars: Iterable[Exemplar] = (),
) -> dict:
    data = finding.asDict()
    exemplar = exemplarFor(finding.rule, preset, customExemplars)
    if exemplar:
        data["exemplar"] = exemplarInRegister(exemplar, register).asDict()
    return data


def renderJson(
    results: dict[str, list[Finding]],
    audits: dict[str, AuditResult] | None = None,
    configLabel: str | None = None,
    registers: dict[str, str] | None = None,
    preset: str | None = None,
    customExemplars: Iterable[Exemplar] = (),
) -> str:
    files = []
    for path, findings in results.items():
        register = registers.get(path) if registers else None
        entry: dict = {
            "path": path,
            "findings": [findingWithExemplar(f, register, preset, customExemplars) for f in findings],
        }
        if audits and path in audits:
            entry["audit"] = audits[path].asDict()
        files.append(entry)
    data: dict = {"version": 1}
    if configLabel is not None:
        data["config"] = configLabel
    data["files"] = files
    return json.dumps(data, ensure_ascii=False, indent=2)
