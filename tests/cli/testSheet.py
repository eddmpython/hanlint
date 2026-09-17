"""`hanlint sheet` 명령줄 계약. 표를 내고, 고친 표를 파일에 되돌려 쓴다."""

from __future__ import annotations

import os
from pathlib import Path

from hanlint.cli.main import main

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "sheet"


def testSheetListsFlaggedTextOnly(capsys):
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        assert main(["sheet", "tests/fixtures/sheet", "--preset", "screen"]) == 0
    finally:
        os.chdir(cwd)
    out = capsys.readouterr().out
    assert "| 1 | tests/fixtures/sheet/sample.jsx:4:45 | 요청을 완료하지 못했습니다 | screenSentence:" in out
    assert "승인 대기" not in out
    assert "개발자만 보는 줄" not in out and "시험 문자열" not in out


def testSheetAllIncludesCleanText(capsys):
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        assert main(["sheet", "tests/fixtures/sheet", "--preset", "screen", "--all", "--format", "json"]) == 0
    finally:
        os.chdir(cwd)
    assert '"text": "승인 대기"' in capsys.readouterr().out


def testApplyWritesFixesBackAndReportsFailures(tmp_path, capsys):
    source = tmp_path / "sample.js"
    source.write_text("const a = '요청을 완료하지 못했습니다'\nconst b = '둘'\n", encoding="utf-8")
    sheet = tmp_path / "sheet.md"
    label = source.as_posix()
    sheet.write_text(
        "| 번호 | 자리 | 글 | 지적 | 고침 |\n| --- | --- | --- | --- | --- |\n"
        f"| 1 | {label}:1 | 요청을 완료하지 못했습니다 | x | 요청 실패 |\n"
        f"| 2 | {label}:2 | 없는 글 | x | 셋 |\n"
        f"| 3 | {label}:9 | 둘 | x | 셋 |\n"
        f"| 4 | {label}:2:5 | 둘 | x | 넷 |\n",
        encoding="utf-8",
    )
    assert main(["sheet", "apply", str(sheet), "--dry-run"]) == 1
    assert source.read_text(encoding="utf-8").startswith("const a = '요청을 완료하지 못했습니다'")
    assert main(["sheet", "apply", str(sheet)]) == 1
    out = capsys.readouterr().out
    assert "적용 1건, 실패 3건" in out
    assert f"{label}:2: 글이 그 줄에 0번 있다" in out and f"{label}:9: 그 줄이 없다" in out
    assert f"{label}:2:5: 그 칸에 그 글이 없다" in out
    assert source.read_text(encoding="utf-8") == "const a = '요청 실패'\nconst b = '둘'\n"
    sheet.write_text(
        f"| 번호 | 자리 | 글 | 지적 | 고침 |\n| --- | --- | --- | --- | --- |\n| 1 | {label}:2:12 | 둘 | x | 넷 |\n",
        encoding="utf-8",
    )
    assert main(["sheet", "apply", str(sheet)]) == 0
    assert source.read_text(encoding="utf-8") == "const a = '요청 실패'\nconst b = '넷'\n"


def testApplyChangesSeveralPlacesOnOneLineFromTheBack(tmp_path):
    """앞 칸을 먼저 바꾸면 길이가 달라져 뒤 칸이 어긋난다. 표의 순서와 상관없이 뒤 칸부터 바꾼다."""
    source = tmp_path / "sample.js"
    source.write_text("const t = { a: '데이터 삭제', b: '기기 삭제' }\n", encoding="utf-8")
    sheet = tmp_path / "sheet.md"
    label = source.as_posix()
    sheet.write_text(
        "| 번호 | 자리 | 글 | 지적 | 고침 |\n| --- | --- | --- | --- | --- |\n"
        f"| 1 | {label}:1:17 | 데이터 삭제 | x | 자료 삭제 |\n"
        f"| 2 | {label}:1:30 | 기기 삭제 | x | 이 컴퓨터 삭제 |\n",
        encoding="utf-8",
    )
    assert main(["sheet", "apply", str(sheet)]) == 0
    assert source.read_text(encoding="utf-8") == "const t = { a: '자료 삭제', b: '이 컴퓨터 삭제' }\n"
