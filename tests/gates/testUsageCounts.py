"""실린 용례 빈도표는 scripts/derive/usageCounts.py 의 계약 (크기 상한, 정렬, 최소 문서 수, 최소 길이) 을 지킨다."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.derive.usageCounts import MAX_BYTES, MIN_DOCUMENTS, MIN_LENGTH, problems, tablePath

from hanlint.config import USAGE_KINDS


def testShippedTablesKeepTheContract():
    for kind in USAGE_KINDS:
        path = tablePath(kind)
        assert path.exists(), f"{path.name} 이 없다. python scripts/derive/usageCounts.py --kind {kind} 를 돌린다"
        assert problems(path) == []


def testGateSeesABrokenTable(tmp_path: Path):
    good = {"kind": "report", "minLength": MIN_LENGTH, "minDocuments": MIN_DOCUMENTS}
    oversized = tmp_path / "usageCounts.report.json"
    oversized.write_text(json.dumps({**good, "chains": {"가나 나다 다라 라마": 3}}) + " " * (MAX_BYTES + 1), encoding="utf-8")
    assert any("바이트" in problem for problem in problems(oversized))

    unsorted = tmp_path / "usageCounts.report.json"
    unsorted.write_text(json.dumps({**good, "chains": {"나나 나나 나나 나나": 3, "가가 가가 가가 가가": 3}}), encoding="utf-8")
    assert any("정렬" in problem for problem in problems(unsorted))

    thin = tmp_path / "usageCounts.report.json"
    chains = {"가상환경 생성 후 패키지": 1, "익 잉 여 금": 3, "짧은 연쇄 둘": 3}
    thin.write_text(json.dumps({**good, "chains": chains}), encoding="utf-8")
    found = problems(thin)
    assert len(found) == 4 and "이상의 정수" in found[0] and "글자 하나" in found[1] and "미만" in found[2]
    assert "patterns" in found[3]

    patterns = {"translationese": {"에 대한": 1, "없는 항목": 2}, "spelling": {"x": 1}}
    okay = {**good, "documents": 3, "chains": {"가나 나다 다라 라마": 3}}
    odd = tmp_path / "usageCounts.report.json"
    odd.write_text(json.dumps({**okay, "patterns": patterns}), encoding="utf-8")
    found = problems(odd)
    assert any("사전에 없는 항목" in problem for problem in found)
    assert any("정렬" in problem for problem in found) and any("표에 드는 사전이 아니다" in problem for problem in found)
    fine = tmp_path / "usageCounts.report.json"
    fine.write_text(json.dumps({**okay, "patterns": {"translationese": {"에 대한": 3}}}), encoding="utf-8")
    assert problems(fine) == []
