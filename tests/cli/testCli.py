"""명령줄 계약. 종료 코드 0 (지적 없음), 1 (error 지적), 2 (파일이나 설정 문제)."""

from __future__ import annotations

import io
import json
from pathlib import Path

from hanlint.cli.main import main, normalizeArgv

BAD = "## 절\n\n핵심은 속도입니다.\n"
CLEAN = "## 절\n\n파일을 엽니다. 그러면 표가 생길까요? 작업 폴더에 생깁니다.\n"
MIXED = "## 절\n\n핵심은 속도입니다. 파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다.\n"


DOCLIKE = (
    "# 설정 파일 형식\n\n이 문서는 설정 파일의 키를 정의한다. 키마다 형과 기본값이 있다.\n\n"
    "## 위치\n\n프로그램은 현재 폴더에서 파일을 찾는다. 없으면 상위로 올라간다.\n\n"
    "## 우선순위\n\n환경 변수가 파일을 이긴다. 그래서 명령줄 인자가 가장 강하다.\n"
)
"""블로그 프리셋에서는 독자를 안 부른다고 잡히고 docs 프리셋에서는 안 잡히는 글."""


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


def testLearnEmitsReviewableTextJsonAndToml(tmp_path, capsys):
    before = write(tmp_path, "전.md", "설계에 대한 이해가 필요합니다.\n")
    after = write(tmp_path, "후.md", "설계를 알아야 합니다.\n")
    assert main(["learn", str(before), str(after)]) == 0
    text = capsys.readouterr().out
    assert "본보기 후보" in text and "[translationese]" in text and "사람이 뜻을 확인" in text

    assert main(["learn", str(before), str(after), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    candidate = next(item for item in data["candidates"] if item["rule"] == "translationese")
    assert candidate["beforeLine"] == 1 and candidate["presets"] == ["blog"]

    assert main(["learn", str(before), str(after), "--format", "toml"]) == 0
    toml = capsys.readouterr().out
    assert "[[exemplars]]" in toml and 'rule = "translationese"' in toml and 'presets = ["blog"]' in toml


def testProjectExemplarReachesLintRulesAndExplain(tmp_path, capsys):
    config = write(
        tmp_path,
        "hanlint.toml",
        '[[exemplars]]\nrule = "cliche"\nbefore = "조직 전입니다."\nafter = "조직 후입니다."\n'
        'moved = "결론을 직접 씀"\npresets = ["blog"]\n',
    )
    bad = write(tmp_path, "bad.md", BAD)
    assert main([str(bad), "--config", str(config), "--format", "json"]) == 1
    lintData = json.loads(capsys.readouterr().out)
    cliche = next(item for item in lintData["files"][0]["findings"] if item["rule"] == "cliche")
    assert cliche["exemplar"]["before"] == "조직 전입니다."

    assert main(["rules", "--config", str(config), "--format", "json"]) == 0
    rulesData = json.loads(capsys.readouterr().out)
    assert next(item for item in rulesData["rules"] if item["name"] == "cliche")["exemplar"]["before"] == "조직 전입니다."

    assert main(["explain", "cliche", "--config", str(config), "--format", "json"]) == 0
    explainData = json.loads(capsys.readouterr().out)
    assert explainData["exemplar"]["before"] == "조직 전입니다."


def testSeverityFiltersAndCompactFormat(tmp_path, capsys):
    mixed = write(tmp_path, "mixed.md", MIXED)
    assert main([str(mixed), "--format", "compact", "--quiet"]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert any(line.startswith(f"{mixed}:3 [cliche] ") for line in lines)
    assert any("[factListParagraph]" in line or "[endingRepeat]" in line for line in lines)
    assert lines[-1].startswith("파일 1개, error 1, notice ")
    # 요약은 거른 뒤가 아니라 글에 있는 것을 센다. 보여 줄 것을 고르는 옵션이 수를 바꾸면 거짓말이다.
    assert main([str(mixed), "--format", "compact", "--errors-only", "--quiet"]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"{mixed}:3 [cliche] `핵심은` 결론을 포장하는 말이다. 핵심이 무엇인지 그 자리에서 직접 쓴다 (글쓰기 스킬)"
    assert lines[-1].startswith("파일 1개, error 1, notice ") and not lines[-1].endswith("notice 0")
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
    assert "왜:" in doc and "고치기:" in doc and "기제: dictionary." in doc
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
    assert any(f["rule"] == "outsideProfile" and f["severity"] == "notice" and "문장 길이" in f["why"] for f in findings)
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["profile", "build", str(empty)]) == 2


def testTermsShowsLearningGradeAndOptionalOutsideWord(tmp_path, capsys):
    draft = tmp_path / "학습자.md"
    draft.write_text("학교에 갑니다. 갈등을 줄입니다. 새기능을 설명합니다.\n", encoding="utf-8")

    assert main(["terms", str(draft)]) == 0
    output = capsys.readouterr().out
    assert "[C] 갈등" in output
    assert "새기능" not in output
    assert "한국어 학습용 어휘 목록" in output

    assert main(["terms", str(draft), "--outside", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    terms = data["files"][0]["terms"]
    assert {term["word"] for term in terms} >= {"갈등", "새기능"}
    assert next(term for term in terms if term["word"] == "새기능")["outside"] is True


def testPresetSelectsContextualExemplar(tmp_path, capsys):
    draft = tmp_path / "보고서.md"
    draft.write_text("지역 경제 활성화 지원 사업 추진 계획을 발표했습니다.\n", encoding="utf-8")
    assert main([str(draft), "--preset", "report", "--format", "json"]) == 1
    findings = json.loads(capsys.readouterr().out)["files"][0]["findings"]
    nounPile = next(finding for finding in findings if finding["rule"] == "nounPile")
    assert nounPile["exemplar"]["before"].startswith("지역 경제")

    assert main(["explain", "nounPile", "--preset", "docs", "--format", "json"]) == 0
    explained = json.loads(capsys.readouterr().out)
    assert explained["exemplar"]["before"].startswith("사용자 인증")


def testInitWritesConfigAndRefusesToOverwrite(tmp_path, capsys):
    target = tmp_path / "hanlint.toml"
    assert main(["init", "--output", str(target)]) == 0
    text = target.read_text(encoding="utf-8")
    assert "disable = []" in text and "#   doublePassive:" in text
    assert main(["init", "--output", str(target)]) == 2
    assert "이미 있다" in capsys.readouterr().err
    assert main(["init", "--output", str(target), "--force"]) == 0


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
    assert "이 폴더에는 검사할 마크다운이 없다" in out


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
    assert main(["init", "--output", str(target), "--preset", "docs"]) == 0
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


def testWatchRunsOnceAndSeesChanges(tmp_path, capsys):
    """감시는 파일이 바뀔 때만 다시 검사한다. 시험은 `rounds` 로 도는 횟수를 묶는다."""
    from hanlint.cli.commands import watch
    from hanlint.cli.main import buildParser

    draft = write(tmp_path, "초안.md", BAD)
    args = buildParser().parse_args(["watch", str(draft), "--format", "compact", "--quiet"])
    assert watch.run(args, rounds=1) == 0
    first = capsys.readouterr().out
    assert "[cliche]" in first and "다음: error" in first

    stamps = watch.stampOf([str(draft)])
    draft.write_text(CLEAN, encoding="utf-8")
    assert watch.stampOf([str(draft)]) != stamps
    args = buildParser().parse_args(["watch", str(draft), "--format", "compact", "--quiet"])
    assert watch.run(args, rounds=1) == 0
    assert "다음: 세어서 잡히는 결함이 없다" in capsys.readouterr().out


def testWatchAcceptsFolders(tmp_path, capsys):
    from hanlint.cli.commands import watch
    from hanlint.cli.main import buildParser

    (tmp_path / "글들").mkdir()
    (tmp_path / "글들" / "하나.md").write_text(BAD, encoding="utf-8")
    (tmp_path / "글들" / "둘.md").write_text(CLEAN, encoding="utf-8")
    args = buildParser().parse_args(["watch", str(tmp_path / "글들"), "--format", "compact"])
    assert watch.run(args, rounds=1) == 0
    out = capsys.readouterr().out
    assert "2개를 지켜본다" in out and "파일 2개" in out


def testBaselineLocksThenLintPasses(tmp_path, capsys):
    """도입의 벽. 이미 쓴 글이 error 를 내도 잠근 뒤에는 새로 생긴 것만 막는다."""
    draft = write(tmp_path, "초안.md", BAD)
    lock = tmp_path / ".hanlint-baseline.json"
    assert main([str(draft), "--no-color"]) == 1
    capsys.readouterr()

    assert main(["baseline", str(draft), "--output", str(lock)]) == 0
    out = capsys.readouterr().out
    assert "1건을 적었다" in out and "1개 글의 지적을 잠갔다" in out
    assert json.loads(lock.read_text(encoding="utf-8"))["files"]["초안.md"][0]["rule"] == "cliche"

    assert main([str(draft), "--baseline", str(lock), "--format", "compact"]) == 0
    out = capsys.readouterr().out
    assert "error 0" in out and "잠근 자리 1건은 넘겼다" in out


def testBaselineDoesNotHideNewProblems(tmp_path, capsys):
    draft = write(tmp_path, "초안.md", BAD)
    lock = tmp_path / ".hanlint-baseline.json"
    main(["baseline", str(draft), "--output", str(lock)])
    capsys.readouterr()

    draft.write_text(BAD + "\n핵심은 결국 새로 잰 속도입니다.\n", encoding="utf-8")
    assert main([str(draft), "--baseline", str(lock), "--format", "compact"]) == 1
    assert "[cliche]" in capsys.readouterr().out


def testBaselinePruneDropsDeadLocks(tmp_path, capsys):
    draft = write(tmp_path, "초안.md", BAD)
    lock = tmp_path / ".hanlint-baseline.json"
    main(["baseline", str(draft), "--output", str(lock)])
    draft.write_text(CLEAN, encoding="utf-8")
    capsys.readouterr()

    assert main(["baseline", str(draft), "--prune", "--output", str(lock)]) == 0
    assert "0건을 적었다" in capsys.readouterr().out
    assert json.loads(lock.read_text(encoding="utf-8"))["files"] == {}


def testDoctorShowsLockedDebt(tmp_path, capsys, monkeypatch):
    """잠금이 빚을 감추는 자리가 되지 않게 doctor 가 늘 몇 건인지 말한다."""
    draft = write(tmp_path, "초안.md", BAD)
    lock = tmp_path / ".hanlint-baseline.json"
    main(["baseline", str(draft), "--output", str(lock)])
    write(tmp_path, "hanlint.toml", 'baseline = ".hanlint-baseline.json"\n')
    monkeypatch.chdir(tmp_path)
    capsys.readouterr()

    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "잠금      1건이" in out

    (tmp_path / ".hanlint-baseline.json").unlink()
    assert main(["doctor"]) == 0
    assert "못 읽었다" in capsys.readouterr().out


def testMissingBaselineFileIsAnErrorNotSilence(tmp_path, capsys):
    """없는 잠금 파일을 조용히 빈 잠금으로 보면 CI 가 오타를 못 본다."""
    draft = write(tmp_path, "초안.md", BAD)
    assert main([str(draft), "--baseline", str(tmp_path / "없다.json")]) == 2
    assert "찾지 못했다" in capsys.readouterr().err


def testPresetFlagWorksWithoutAConfigFile(tmp_path, capsys):
    """글 하나를 검사하려고 남의 저장소에 hanlint.toml 을 만들게 하지 않는다."""
    doc = write(tmp_path, "문서.md", DOCLIKE)
    assert main([str(doc), "--format", "compact"]) == 1
    blog = capsys.readouterr().out
    assert "[noQuestion]" in blog

    assert main([str(doc), "--preset", "docs", "--format", "compact"]) == 0
    docs = capsys.readouterr().out
    assert "[noQuestion]" not in docs
    assert docs.startswith("설정: 기본값, 프리셋 docs\n")


def testHeaderNamesThePresetOnlyWhenItIsNotTheDefault(tmp_path, capsys):
    doc = write(tmp_path, "초안.md", CLEAN)
    main([str(doc), "--format", "compact"])
    assert capsys.readouterr().out.startswith("설정: 기본값\n")
    main([str(doc), "--preset", "report", "--format", "compact"])
    assert capsys.readouterr().out.startswith("설정: 기본값, 프리셋 report\n")


def testUnknownPresetIsRefused(tmp_path, capsys):
    doc = write(tmp_path, "초안.md", CLEAN)
    with __import__("pytest").raises(SystemExit):
        main([str(doc), "--preset", "없는것"])
    assert "invalid choice" in capsys.readouterr().err


def testNextStepPointsAtTheBiggestPile():
    """한 줄뿐인 다음 걸음이 가장 작은 더미를 가리키면 안 된다. 알파벳 순은 사용자에게 뜻이 없다."""
    from hanlint.cli.commands.shared import commonest
    from hanlint.rules import Finding

    def finding(rule):
        return Finding(rule, 1, "인용", "왜")

    errors = [finding("cliche"), finding("cliche"), finding("noQuestion"), finding("noQuestion"), finding("noQuestion")]
    assert commonest(errors) == "noQuestion"
    assert commonest([finding("zebra"), finding("apple")]) == "apple"


def testFolderWalkSkipsForeignPackages(tmp_path, capsys):
    """실측: 블로그 저장소에서 `hanlint .` 이 남의 패키지까지 훑어 error 305건을 냈고 내 글은 97% 지점에 있었다."""
    (tmp_path / "posts").mkdir()
    write(tmp_path / "posts", "글.md", CLEAN)
    for folder in ("node_modules", ".git", ".venv"):
        (tmp_path / folder).mkdir()
        write(tmp_path / folder, "README.md", BAD)

    assert main([str(tmp_path), "--format", "compact", "--quiet"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "파일 1개, error 0, notice 0"

    # 명시가 규칙을 이긴다. 그 폴더를 직접 주면 검사한다
    assert main([str(tmp_path / "node_modules"), "--format", "compact", "--quiet"]) == 1
    assert "파일 1개, error 1" in capsys.readouterr().out


def testFixDoesNotTouchSkippedFolders(tmp_path, capsys):
    """실측: `hanlint fix .` 이 npm 과 pip 가 소유한 파일을 원문 그대로 덮어썼다."""
    (tmp_path / "node_modules").mkdir()
    theirs = write(tmp_path / "node_modules", "README.md", "# pkg\n\n모든 분야에 있어서 기준이 필요합니다.\n")
    (tmp_path / "posts").mkdir()
    write(tmp_path / "posts", "글.md", CLEAN)
    before = theirs.read_text(encoding="utf-8")

    assert main(["fix", str(tmp_path)]) == 0
    capsys.readouterr()
    assert theirs.read_text(encoding="utf-8") == before


def testWelcomeAgreesWithWhatLintWillCheck(tmp_path, capsys, monkeypatch):
    """실측: posts/ 에 글을 둔 저장소에서 첫 화면은 없다고 하고 `hanlint .` 은 찾았다."""
    (tmp_path / "posts").mkdir()
    write(tmp_path / "posts", "도구.md", CLEAN)
    monkeypatch.chdir(tmp_path)

    assert main([]) == 0
    out = capsys.readouterr().out
    assert "hanlint posts/도구.md" in out
    assert "이 폴더의 마크다운: posts/도구.md" in out


def testFolderCommandsSayFolderInsteadOfCrashing(tmp_path, capsys):
    """실측: `hanlint audit 글들/` 이 파이썬 PermissionError 트레이스백을 뱉었다."""
    (tmp_path / "글들").mkdir()
    write(tmp_path / "글들", "하나.md", CLEAN)
    for command in ("audit", "map", "print"):
        assert main([command, str(tmp_path / "글들")]) == 2, command
        assert "는 폴더다" in capsys.readouterr().err, command


def testUnknownSubcommandIsNotTreatedAsAPath(capsys):
    """실측: `hanlint rulez` 가 `경로를 확인하라` 고 해서 엉뚱한 데를 뒤지게 했다."""
    assert main(["rulez"]) == 2
    error = capsys.readouterr().err
    assert "모르는 명령이다" in error and "rules" in error


def testFixPromiseMatchesWhatFixDoes(tmp_path, capsys):
    """실측: `1건은 hanlint fix 가 바로 고친다` 라고 하고 fix 는 `0곳 고침, 1곳 건너뜀` 을 냈다."""
    text = "## 절\n\n그래서 `에 있어서` 를 봅니다. 따라서 파일을 엽니다. 그러면 표가 보입니다.\n"
    draft = write(tmp_path, "초안.md", text)
    main([str(draft), "--format", "compact", "--quiet"])
    said = capsys.readouterr().out
    main(["fix", str(draft), "--dry-run"])
    did = capsys.readouterr().out
    assert ("hanlint fix 가 바로 고친다" in said) == ("0곳 고침" not in did)


def testCompactKeepsOneLinePerFinding(tmp_path, capsys):
    """실측: 두 줄에 걸친 문장의 고침 제안이 줄바꿈을 들고 나와 grep 이 반토막을 냈다."""
    wrapped = "# 제목\n\n첫 문단입니다.\n\n## 절\n\n그리고 이것을 통해\n우리는 문제를 해결할수 있습니다. 다음입니다.\n"
    draft = write(tmp_path, "접힌.md", wrapped)
    assert main([str(draft), "--format", "compact", "--quiet"]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert all(line.startswith(str(draft)) for line in lines[:-1]), lines
    assert lines[-1].startswith("파일 1개, ")


def testLineNumberPointsAtTheWordNotTheSentenceStart(tmp_path, capsys):
    """실측: 8행의 `할수 있` 을 7행이라 적어 github 주석과 편집기 점프가 멀쩡한 줄로 갔다."""
    wrapped = "# 제목\n\n첫 문단입니다.\n\n## 절\n\n그리고 이것을 통해\n우리는 문제를 해결할수 있습니다. 다음입니다.\n"
    draft = write(tmp_path, "접힌.md", wrapped)
    assert main([str(draft), "--format", "compact", "--quiet"]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert any(line.startswith(f"{draft}:8 [spacing]") for line in lines), lines
    # 고침이 그 자리를 여전히 잡는다
    assert main(["fix", str(draft), "--dry-run"]) == 0
    assert f"{draft}:8  할수 있 → 할 수 있" in capsys.readouterr().out


def testFixSaysWhatIsLeftByHand(tmp_path, capsys):
    """실측: `0곳 고침, 0곳 건너뜀` 만 보면 손볼 것이 없다는 뜻으로 읽힌다."""
    draft = write(tmp_path, "초안.md", "# 시험\n\n설계에 대한 이해가 부족했다. 그래서 봅니다. 따라서 씁니다.\n")
    assert main(["fix", str(draft), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "0곳 고침, 0곳 건너뜀" in out and "손으로 고칠 error 1건이 남았다" in out

    clean = write(tmp_path, "깨끗.md", CLEAN)
    assert main(["fix", str(clean), "--dry-run"]) == 0
    assert "남았다" not in capsys.readouterr().out


def testExplainTellsWhereToReportAFalsePositive(capsys):
    """오탐이라고 판단한 사람에게 끄는 법만 알려 주면 규칙은 틀린 채로 남는다."""
    assert main(["explain", "danglingDeixis"]) == 0
    assert "알려 준다: github.com/eddmpython/hanlint/issues" in capsys.readouterr().out


def testMapKeepsTheSectionTitleWhole(tmp_path, capsys):
    """실측: 절 배지가 제목의 첫 글자를 덮어써서 `단계별` 이 `S계별` 이 됐다."""
    text = "# 제목\n\n도입입니다. 그래서 씁니다.\n\n## 단계별 시간을 잰 표\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    draft = write(tmp_path, "지도.md", text)
    assert main(["map", str(draft), "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "단계별" in out and "S계별" not in out
    assert "기호: S 구조" in out
