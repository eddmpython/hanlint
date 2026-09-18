"""`hanlint usage` 명령줄 계약. 색인이 없으면 만드는 법을 알리고 2, build 는 만들고, 질의는 문장을 보인다."""

from __future__ import annotations

import json
from pathlib import Path

from hanlint.cli.main import main

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "fixtures" / "usage" / "corpus"


def testMissingIndexExplainsHowToBuild(tmp_path, capsys):
    assert main(["usage", "리스부채", "--root", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "report 색인이 없다" in out and "hanlint usage build report" in out


def testBuildThenQueryTextAndJson(tmp_path, capsys):
    assert main(["usage", "build", "report", str(CORPUS), "--root", str(tmp_path)]) == 0
    assert "문서 3편, 문장 11개" in capsys.readouterr().out
    assert main(["usage", "리스부채", "측정", "--root", str(tmp_path), "--limit", "1"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("report 용례 (문서 3편, 문장 11개): 리스부채 측정\n1. 회사는 리스부채를")
    assert "   문서 3편, 출처 a001" in out
    assert main(["usage", "영업이익 감소 원인", "--root", str(tmp_path), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["kind"] == "report" and data["query"] == "영업이익 감소 원인" and data["sentences"] == 11
    assert data["hits"][0]["text"] == "영업이익 감소의 주요 원인은 원재료 가격 상승입니다."
    assert set(data["hits"][0]) == {"text", "documents", "source", "score"}
    assert main(["usage", "없는낱말", "--root", str(tmp_path)]) == 0
    assert "쓰인 문장이 없다" in capsys.readouterr().out


def testBuildArgumentsAreChecked(tmp_path, capsys):
    assert main(["usage", "build", "report", "--root", str(tmp_path)]) == 2
    assert "hanlint usage build <종류> <글 폴더>" in capsys.readouterr().out
    assert main(["usage", "build", "report", str(tmp_path / "없는폴더"), "--root", str(tmp_path)]) == 2
    assert "폴더가 아니다" in capsys.readouterr().out
