"""글 시트의 표 렌더와 되읽기. 칸의 `|` 는 이스케이프되고, 고침이 있는 줄만 돌아온다."""

from __future__ import annotations

import json

from hanlint.report import SheetRow, parseSheet, renderSheet, renderSheetJson
from hanlint.rules import Finding


def finding(rule: str, why: str) -> Finding:
    return Finding(rule, 1, "글", why, None, "error", "sentence", 0)


ROWS = [
    SheetRow("src/a.jsx", 4, "요청을 완료하지 못했습니다", (finding("screenSentence", "실패를 문장으로 쓴 것이다"),)),
    SheetRow("src/a.jsx", 9, "값 | 단위", ()),
]


def testRenderAndParseRoundTrip():
    sheet = renderSheet(ROWS, "screen", 1)
    assert "| 1 | src/a.jsx:4 | 요청을 완료하지 못했습니다 | screenSentence: 실패를 문장으로 쓴 것이다 |  |" in sheet
    assert "| 2 | src/a.jsx:9 | 값 \\| 단위 |  |  |" in sheet
    edited = sheet.replace("실패를 문장으로 쓴 것이다 |  |", "실패를 문장으로 쓴 것이다 | 요청 실패 |")
    edited = edited.replace("| 값 \\| 단위 |  |  |", "| 값 \\| 단위 |  | 값 \\| 단위 x |")
    parsed = parseSheet(edited)
    assert parsed.problems == []
    assert [(row.file, row.line, row.text, row.fix) for row in parsed.rows] == [
        ("src/a.jsx", 4, "요청을 완료하지 못했습니다", "요청 실패"),
        ("src/a.jsx", 9, "값 | 단위", "값 | 단위 x"),
    ]


def testParseReportsBadRows():
    parsed = parseSheet("| 1 | 자리없음 | 글 | 지적 | 고침 |\n| 2 | a:1 | 글 |\n")
    assert parsed.rows == []
    assert parsed.problems == ["1행: 자리 `자리없음` 가 경로:줄 이나 경로:줄:칸 꼴이 아니다", "2행: 칸이 3개다. 5개여야 한다"]


def testJsonCarriesFindingsAndFix():
    data = json.loads(renderSheetJson(ROWS, "screen", 1))
    assert data["version"] == 1 and data["files"] == 1 and data["preset"] == "screen"
    assert data["rows"][0]["findings"] == [{"rule": "screenSentence", "why": "실패를 문장으로 쓴 것이다"}]
    assert data["rows"][1]["fix"] == ""
