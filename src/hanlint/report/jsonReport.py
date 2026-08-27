"""기계가 읽는 꼴. 평가 루프의 0층 입력이다. textlint 의 message 와 필드가 대응한다."""

from __future__ import annotations

import json

from ..audit import AuditResult
from ..rules import Finding


def renderJson(results: dict[str, list[Finding]], audits: dict[str, AuditResult] | None = None) -> str:
    files = []
    for path, findings in results.items():
        entry: dict = {"path": path, "findings": [f.asDict() for f in findings]}
        if audits and path in audits:
            entry["audit"] = audits[path].asDict()
        files.append(entry)
    return json.dumps({"version": 1, "files": files}, ensure_ascii=False, indent=2)
