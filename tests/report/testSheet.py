"""글 시트의 표 렌더와 되읽기. 칸의 `|` 는 이스케이프되고, 고침이 있는 줄만 돌아온다."""

from __future__ import annotations

import json

from hanlint.config import Config
from hanlint.report import SheetRow, parseSheet, renderSheet, renderSheetJson, sheetRows
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


SOURCE = "const LABELS = { pending: '승인 대기', failed: '요청을 완료하지 못했습니다' }\nconst NOTE = '없음'\n"


def testSheetRowsKeepOnlyFlaggedTextUnlessEverything():
    """소스 문자열만 받아 행을 만든다. 지적 없는 글은 everything 일 때만 들어가고 고침은 지적이 하나일 때 미리 적힌다."""
    config = Config(preset="screen")
    rows = sheetRows([("src/a.jsx", SOURCE)], config)
    assert [(row.file, row.line, row.column, row.text) for row in rows] == [("src/a.jsx", 1, 45, "요청을 완료하지 못했습니다")]
    assert rows[0].findings[0].rule == "screenSentence" and rows[0].fix == "요청 완료 실패"
    passive = sheetRows([("src/b.js", "const MSG = '결과가 저장되어집니다'" + chr(10))], config)
    assert [(row.findings[0].rule, row.fix) for row in passive] == [("doublePassive", "결과가 저장됩니다")]
    everything = sheetRows([("src/a.jsx", SOURCE)], config, everything=True)
    assert [row.text for row in everything] == ["승인 대기", "요청을 완료하지 못했습니다", "없음"]
    assert everything[0].findings == () and everything[0].fix == ""


def testFindingCellNamesEachRuleOnceAndListsExtraCues():
    """같은 규칙의 지적이 여럿이면 첫 이유만 온전히 쓰고 나머지는 단서만 `(또 …)` 로 잇는다. 다른 규칙은 ` / ` 로 나눈다."""
    rows = [
        SheetRow(
            "a.js",
            1,
            "글",
            (
                finding("screenSentence", "`니다.` 는 종결어미다"),
                finding("screenSentence", "`습니다` 는 종결어미다"),
                finding("doublePassive", "`되어지` 는 이중 피동이다"),
                finding("screenSentence", "`세요` 는 종결어미다"),
            ),
        ),
        SheetRow("a.js", 2, "글", (finding("nounPile", "명사 6개가 이어진다"), finding("nounPile", "명사 5개가 이어진다"))),
    ]
    sheet = renderSheet(rows, "screen", 1)
    assert "| screenSentence: `니다.` 는 종결어미다 (또 `습니다`, `세요`) / doublePassive: `되어지` 는 이중 피동이다 |" in sheet
    assert "| nounPile: 명사 6개가 이어진다 (또 1건) |" in sheet
