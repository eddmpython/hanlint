"""명령줄 계약. 종료 코드 0 (지적 없음), 1 (error 지적), 2 (파일이나 설정 문제)."""

from __future__ import annotations

import json
from pathlib import Path

from hanlint.cli.main import main, normalizeArgv

BAD = "## 절\n\n핵심은 속도입니다.\n"
CLEAN = "## 절\n\n파일을 엽니다. 그러면 표가 생길까요? 작업 폴더에 생깁니다.\n"


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def testNormalizeArgvDefaultsToLint():
    assert normalizeArgv([]) == ["lint"]
    assert normalizeArgv(["글.md"]) == ["lint", "글.md"]
    assert normalizeArgv(["--format", "json", "글.md"]) == ["lint", "--format", "json", "글.md"]
    assert normalizeArgv(["rules"]) == ["rules"]
    assert normalizeArgv(["--version"]) == ["--version"]


def testLintExitCodesAndText(tmp_path, capsys):
    bad = write(tmp_path, "bad.md", BAD)
    assert main([str(bad), "--no-color"]) == 1
    out = capsys.readouterr().out
    assert f"{bad}:3  [cliche]" in out
    clean = write(tmp_path, "clean.md", CLEAN)
    assert main([str(clean)]) == 0
    assert "집은 자리 없음" in capsys.readouterr().out


def testLintJsonAndGithub(tmp_path, capsys):
    bad = write(tmp_path, "bad.md", BAD)
    assert main([str(bad), "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["files"][0]["findings"][0]["rule"] == "cliche"
    assert main(["lint", str(bad), "--format", "github"]) == 1
    assert capsys.readouterr().out.startswith("::error file=")


def testDisableAndOutputFile(tmp_path, capsys):
    bad = write(tmp_path, "bad.md", BAD)
    assert main([str(bad), "--disable", "cliche"]) == 0
    capsys.readouterr()
    target = tmp_path / "out.txt"
    assert main([str(bad), "--output", str(target)]) == 1
    assert "[cliche]" in target.read_text(encoding="utf-8")


def testMissingFileIsTwo(tmp_path, capsys):
    assert main([str(tmp_path / "없는파일.md")]) == 2
    assert "찾지 못했다" in capsys.readouterr().err


def testRulesAndExplain(capsys):
    assert main(["rules"]) == 0
    out = capsys.readouterr().out
    assert "doublePassive" in out and "규칙 " in out
    assert main(["explain", "doublePassive"]) == 0
    doc = capsys.readouterr().out
    assert "왜:" in doc and "고치기:" in doc
    assert main(["explain", "noSuchRule"]) == 2
    assert "모르는 규칙" in capsys.readouterr().err


def testAuditMapAndPrint(tmp_path, capsys):
    bad = write(tmp_path, "bad.md", BAD)
    assert main(["audit", str(bad), "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "문장 길이" in out and "배지" in out or "문장 길이" in out
    html = tmp_path / "map.html"
    assert main(["map", str(bad), "--format", "html", "--output", str(html)]) == 0
    assert html.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert main(["print", str(bad)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["fingerprint"]["sentences"][0]["text"] == "핵심은 속도입니다."


def testProfileBuildAndCompare(tmp_path, capsys):
    reference = tmp_path / "ref"
    reference.mkdir()
    (reference / "a.md").write_text(CLEAN, encoding="utf-8")
    (reference / "b.md").write_text("## 절\n\n파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다.\n", encoding="utf-8")
    profile = tmp_path / "profile.json"
    assert main(["profile", "build", str(reference), "--output", str(profile)]) == 0
    assert "2편" in capsys.readouterr().out
    questions = write(tmp_path, "q.md", "## 절\n\n왜 열까요? 무엇이 보일까요? 몇 열일까요? 고칠까요? 저장할까요?\n")
    assert main([str(questions), "--profile", str(profile), "--format", "json"]) == 0
    findings = json.loads(capsys.readouterr().out)["files"][0]["findings"]
    assert any(f["rule"] == "profile" and f["severity"] == "notice" and "질문 비율" in f["why"] for f in findings)
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["profile", "build", str(empty)]) == 2


def testInitWritesConfigAndRefusesToOverwrite(tmp_path, capsys):
    target = tmp_path / "hanlint.toml"
    assert main(["init", "--path", str(target)]) == 0
    text = target.read_text(encoding="utf-8")
    assert "disable = []" in text and "#   doublePassive:" in text
    assert main(["init", "--path", str(target)]) == 2
    assert "이미 있다" in capsys.readouterr().err
    assert main(["init", "--path", str(target), "--force"]) == 0
