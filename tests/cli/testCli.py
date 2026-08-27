"""명령줄 계약. 종료 코드 0 (지적 없음), 1 (error 지적), 2 (파일이나 설정 문제)."""

from __future__ import annotations

import io
import json
from pathlib import Path

from hanlint.cli.main import main, normalizeArgv

BAD = "## 절\n\n핵심은 속도입니다.\n"
CLEAN = "## 절\n\n파일을 엽니다. 그러면 표가 생길까요? 작업 폴더에 생깁니다.\n"
MIXED = "## 절\n\n핵심은 속도입니다. 파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다.\n"


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def testNormalizeArgvDefaultsToLint():
    assert normalizeArgv(["글.md"]) == ["lint", "글.md"]
    assert normalizeArgv(["--format", "json", "글.md"]) == ["lint", "--format", "json", "글.md"]
    assert normalizeArgv(["rules"]) == ["rules"]
    assert normalizeArgv(["-"]) == ["lint", "-"]
    assert normalizeArgv(["--version"]) == ["--version"]


def testLintExitCodesAndText(tmp_path, capsys):
    bad = write(tmp_path, "bad.md", BAD)
    assert main([str(bad), "--no-color"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("설정: 기본값\n")
    assert f"{bad}:3  [cliche]" in out
    clean = write(tmp_path, "clean.md", CLEAN)
    assert main([str(clean), "--quiet"]) == 0
    out = capsys.readouterr().out
    assert "집은 자리 없음" in out and "설정:" not in out


def testLintJsonAndGithub(tmp_path, capsys):
    bad = write(tmp_path, "bad.md", BAD)
    assert main([str(bad), "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["config"] == "기본값"
    assert data["files"][0]["findings"][0]["rule"] == "cliche"
    assert main(["lint", str(bad), "--format", "github"]) == 1
    assert capsys.readouterr().out.startswith("::error file=")


def testSeverityFiltersAndCompactFormat(tmp_path, capsys):
    mixed = write(tmp_path, "mixed.md", MIXED)
    assert main([str(mixed), "--format", "compact", "--quiet"]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert any(line.startswith(f"{mixed}:3 [cliche] ") for line in lines)
    assert any("[factListParagraph]" in line or "[endingRepeat]" in line for line in lines)
    assert lines[-1].startswith("파일 1개, error 1, notice ")
    assert main([str(mixed), "--format", "compact", "--errors-only", "--quiet"]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        f"{mixed}:3 [cliche] `핵심은` 결론을 포장하는 말이다. 핵심이 무엇인지 그 자리에서 직접 쓴다 (글쓰기 스킬)",
        "파일 1개, error 1, notice 0",
    ]
    assert main([str(mixed), "--severity", "notice", "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["files"][0]["findings"] and all(f["severity"] == "notice" for f in data["files"][0]["findings"])


def testStdinWithPathName(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(BAD.encode("utf-8")), encoding="utf-8"))
    assert main(["-", "--path", "초안.md", "--format", "compact", "--quiet"]) == 1
    assert capsys.readouterr().out.startswith("초안.md:3 [cliche]")


def testSummaryForManyFiles(tmp_path, capsys):
    bad = write(tmp_path, "bad.md", BAD)
    clean = write(tmp_path, "clean.md", CLEAN)
    assert main([str(bad), str(clean), "--quiet"]) == 1
    out = capsys.readouterr().out
    assert out.rstrip().endswith("파일 2개, error 1, notice 0")
    assert "집은 자리 없음" in out


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
    assert "문장 길이" in out
    html = tmp_path / "map.html"
    assert main(["map", str(bad), "--format", "html", "--output", str(html)]) == 0
    assert html.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert main(["print", str(bad)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["layer"] == "all" and data["sentences"][0]["text"] == "핵심은 속도입니다."
    assert data["paragraphs"][0]["sentences"] == [0] and data["sections"][1]["paragraphs"] == [0]
    assert data["document"]["sentenceCount"] == 1
    assert main(["print", str(bad), "--layer", "paragraphs"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data) == {"version", "layer", "paragraphs"}


def testFixAppliesAndDryRunKeepsFile(tmp_path, capsys):
    draft = write(tmp_path, "draft.md", "## 절\n\n모든 분야에 있어서 기준이 필요합니다.\r\n둘째 줄입니다.\r\n")
    raw = draft.read_bytes()
    assert main(["fix", str(draft), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "에 있어서 → 에서" in out and "미리보기" in out
    assert draft.read_bytes() == raw
    assert main(["fix", str(draft)]) == 0
    assert "1곳 고침, 0곳 건너뜀" in capsys.readouterr().out
    fixed = draft.read_bytes()
    assert b"\xeb\xaa\xa8\xeb\x93\xa0 \xeb\xb6\x84\xec\x95\xbc\xec\x97\x90\xec\x84\x9c" in fixed
    assert b"\r\n" in fixed
    assert main([str(draft), "--errors-only", "--format", "compact", "--quiet"]) == 0


def testProfileBuildAndCompare(tmp_path, capsys):
    reference = tmp_path / "ref"
    reference.mkdir()
    (reference / "a.md").write_text(CLEAN, encoding="utf-8")
    (reference / "b.md").write_text("## 절\n\n파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다.\n", encoding="utf-8")
    profile = tmp_path / "profile.json"
    assert main(["profile", "build", str(reference), "--output", str(profile)]) == 0
    assert "2편" in capsys.readouterr().out
    longOne = write(
        tmp_path,
        "long.md",
        "## 절\n\n파일을 열고 표를 확인한 다음 열 다섯 개의 이름을 하나씩 읽어 두고 값을 고친 뒤 저장합니다. "
        "폴더를 만들고 파일을 옮기고 이름을 바꾸고 목록을 다시 보고 끝낸 다음 다시 처음부터 엽니다. "
        "표가 보이면 열의 순서를 적어 두고 값을 고친 뒤 저장하고 닫고 다시 열어 확인합니다. "
        "이름을 바꾼 파일을 목록에서 찾아 열고 표를 확인하고 값을 고치고 저장합니다. "
        "그다음 폴더를 정리하고 파일을 옮기고 목록을 다시 보고 끝냅니다.\n",
    )
    assert main([str(longOne), "--profile", str(profile), "--format", "json"]) == 0
    findings = json.loads(capsys.readouterr().out)["files"][0]["findings"]
    assert any(f["rule"] == "profile" and f["severity"] == "notice" and "문장 길이" in f["why"] for f in findings)
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


def testWelcomeScreenWhenNoArguments(monkeypatch, tmp_path, capsys):
    """인자가 없으면 argparse 오류가 아니라 첫 화면이다. 이 폴더의 파일 이름으로 예시를 만든다."""
    write(tmp_path, "초안.md", CLEAN)
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "hanlint 초안.md" in out
    assert "hanlint fix 초안.md" in out
    assert "이 폴더의 마크다운: 초안.md" in out
    assert "hanlint doctor" in out


def testWelcomeScreenWithoutMarkdownNearby(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "hanlint 글.md" in out
    assert "이 폴더에는 마크다운이 없다" in out


def testFolderArgumentFindsMarkdownBelow(tmp_path, capsys):
    (tmp_path / "글들" / "안").mkdir(parents=True)
    (tmp_path / "글들" / "하나.md").write_text(BAD, encoding="utf-8")
    (tmp_path / "글들" / "안" / "둘.md").write_text(CLEAN, encoding="utf-8")
    (tmp_path / "글들" / "그림.png").write_text("bytes", encoding="utf-8")
    assert main([str(tmp_path / "글들"), "--format", "compact", "--quiet"]) == 1
    out = capsys.readouterr().out
    # 하위 폴더의 글까지 세고 (파일 2개) 마크다운이 아닌 것은 건드리지 않는다.
    assert "하나.md" in out and "그림.png" not in out
    assert "파일 2개" in out


def testEmptyFolderSaysWhatToDo(tmp_path, capsys):
    (tmp_path / "빈").mkdir()
    assert main([str(tmp_path / "빈")]) == 2
    assert "안에 마크다운 파일이 없다" in capsys.readouterr().err


def testNextStepLineTellsWhatToDo(tmp_path, capsys):
    clean = write(tmp_path, "clean.md", CLEAN)
    assert main([str(clean)]) == 0
    assert "다음: 세어서 잡히는 결함이 없다" in capsys.readouterr().out
    bad = write(tmp_path, "bad.md", BAD)
    assert main([str(bad), "--errors-only"]) == 1
    assert "다음: error" in capsys.readouterr().out
    assert main([str(bad), "--errors-only", "--quiet"]) == 1
    assert "다음:" not in capsys.readouterr().out


def testDoctorShowsConfigAnalyzerAndOffRules(tmp_path, capsys):
    config = write(tmp_path, "hanlint.toml", 'preset = "docs"\ndisable = ["cliche"]\n')
    assert main(["doctor", "--config", str(config)]) == 0
    out = capsys.readouterr().out
    assert "프리셋    docs" in out
    assert "cliche" in out and "noQuestion" in out
    assert "개 켜짐" in out


def testPresetTurnsRulesOffAndInitWritesIt(tmp_path, capsys):
    target = tmp_path / "hanlint.toml"
    assert main(["init", "--path", str(target), "--preset", "docs"]) == 0
    assert 'preset = "docs"' in target.read_text(encoding="utf-8")
    assert "preset docs 이" in capsys.readouterr().out
    reference = write(tmp_path, "참고.md", "## 절\n\n파일을 엽니다. 값을 넣습니다.\n")
    assert main([str(reference), "--config", str(target), "--format", "compact", "--quiet"]) == 0
    assert "noQuestion" not in capsys.readouterr().out


def testExplainSuggestsNearNamesAndListsSiblings(capsys):
    assert main(["explain", "doublePasive"]) == 2
    assert "이것을 찾았나: doubleNegative, doublePassive" in capsys.readouterr().err
    assert main(["explain"]) == 2
    assert "부류로 묶어 보려면 hanlint rules" in capsys.readouterr().out
    assert main(["explain", "moreLater"]) == 0
    out = capsys.readouterr().out
    assert "글의 짜임에서 세는 것" in out and "같은 부류:" in out


def testRulesGroupsByCategoryAndMarksOff(tmp_path, capsys):
    config = write(tmp_path, "hanlint.toml", 'preset = "report"\n')
    assert main(["rules", "--config", str(config)]) == 0
    out = capsys.readouterr().out
    assert "문장 안에서 세는 것 (" in out and "표기와 띄어쓰기 (" in out
    assert "(꺼짐)" in out and "preset report 이" in out
    assert main(["rules", "--names"]) == 0
    names = capsys.readouterr().out.splitlines()
    assert names == sorted(names) and "moreLater" in names
