"""`hanlint usage` 명령줄 계약. 색인이 없으면 만드는 법을 알리고 2, build 는 만들고, 질의는 문장을 보인다."""

from __future__ import annotations

import json
from pathlib import Path

from hanlint.cli.main import main

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "fixtures" / "usage" / "corpus"


def testMissingIndexExplainsHowToBuild(tmp_path, capsys):
    assert main(["usage", "임차료", "--root", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "report 색인이 없다 (있는 것: 없음)" in out and "hanlint usage build report" in out
    assert main(["usage", "kinds", "--root", str(tmp_path)]) == 0
    assert "색인이 없다" in capsys.readouterr().out


def testBuildThenQueryTextAndJson(tmp_path, capsys):
    assert main(["usage", "build", "report", str(CORPUS), "--root", str(tmp_path)]) == 0
    assert "문서 3편, 문장 11개" in capsys.readouterr().out
    assert main(["usage", "임차료", "계약", "--root", str(tmp_path), "--limit", "1"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("report 용례 (문서 3편, 문장 11개): 임차료 계약\n함께 쓰는 말 (임차료, 문장 3개에서)\n")
    assert "   뒤 용언: 줄어듭 1편\n   뒤 명사: 계약 1편\n" in out and "\n1. 회사는 창고 임차료를" in out
    assert "   문서 3편, 출처 a001" in out
    assert main(["usage", "영업이익 줄어든 원인", "--root", str(tmp_path), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["kind"] == "report" and data["query"] == "영업이익 줄어든 원인" and data["sentences"] == 11
    assert data["hits"][0]["text"] == "영업이익이 줄어든 주된 원인은 원재료인 구리 값이 오른 것입니다."
    assert set(data["hits"][0]) == {"text", "documents", "source", "score"}
    assert data["version"] == 2 and data["words"][0]["term"] == "영업이익" and data["words"][0]["sampled"] == 4
    assert main(["usage", "없는낱말", "--root", str(tmp_path)]) == 0
    assert "쓰인 문장이 없다" in capsys.readouterr().out
    assert main(["usage", "없는낱말", "--root", str(tmp_path), "--limit", "0"]) == 0
    assert capsys.readouterr().out.strip() == "report 용례 (문서 3편, 문장 11개): 없는낱말"
    assert main(["usage", "kinds", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip().endswith("report: 문서 3편, 문장 11개, 토큰 116종")
    assert main(["usage", "kinds", "--root", str(tmp_path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["kinds"][0]["kind"] == "report"


def testBuildArgumentsAreChecked(tmp_path, capsys):
    assert main(["usage", "build", "report", "--root", str(tmp_path)]) == 2
    assert "hanlint usage build <종류> <글 폴더>" in capsys.readouterr().out
    assert main(["usage", "build", "report", str(tmp_path / "없는폴더"), "--root", str(tmp_path)]) == 2
    assert "폴더가 아니다" in capsys.readouterr().out
