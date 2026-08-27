"""baseline 층. 잠근 지적을 넘기되 손댄 자리는 다시 낸다.

계약 넷을 짝으로 본다. 잠그면 안 나온다, 자리만 옮기면 여전히 안 나온다, 고치면 나온다,
지운 자리의 잠금은 --prune 이 치운다. 셋째가 이 설계의 값이라 특히 양쪽을 본다.
"""

from __future__ import annotations

import json

import pytest

from hanlint import Config
from hanlint.baseline import Baseline, build, load, parse, pathKey, prune, render
from tests.conftest import findingsOf

BAD = "## 절\n\n핵심은 속도입니다. 파일을 엽니다. 표가 보입니다.\n"
MOVED = "## 절\n\n먼저 폴더를 만듭니다. 이름을 바꿉니다. 목록을 봅니다.\n\n핵심은 속도입니다. 파일을 엽니다. 표가 보입니다.\n"
FIXED = "## 절\n\n속도가 30% 빨라집니다. 파일을 엽니다. 표가 보입니다.\n"


def lockOf(text: str, name: str = "글.md") -> tuple[Baseline, list]:
    findings = findingsOf(text, Config())
    assert findings, "이 표본은 지적이 나와야 한다"
    return build({name: findings}), findings


def testLockedFindingsAreSkipped():
    baseline, findings = lockOf(BAD)
    assert baseline.count == len(findings)
    assert baseline.keep("글.md", findings) == []


def testMovedTextStaysLocked():
    """줄 번호가 아니라 글자로 잠그므로 문단이 밀려도 잠긴 채다. 코드 린터의 baseline 이 못 하는 자리."""
    baseline, _ = lockOf(BAD)
    moved = findingsOf(MOVED, Config())
    kept = baseline.keep("글.md", moved)
    assert not [f for f in kept if f.rule == "cliche"]
    assert all(f.line > 3 or f.rule != "cliche" for f in moved)


def testEditedTextComesBack():
    """손댔으면 책임진다. 인용문이 달라지면 새 지적이다."""
    baseline, _ = lockOf(BAD)
    after = findingsOf(FIXED, Config())
    assert not [f for f in baseline.keep("글.md", after) if f.rule == "cliche"]
    changed = "## 절\n\n핵심은 속도이고 무엇보다 중요합니다. 파일을 엽니다. 표가 보입니다.\n"
    assert [f for f in baseline.keep("글.md", findingsOf(changed, Config())) if f.rule == "cliche"]


def testQuoteIsNormalizedAcrossReflow():
    """문단을 다시 흘려 줄바꿈이 문장 가운데로 들어가도 같은 문장이다."""
    baseline, _ = lockOf(BAD)
    reflowed = findingsOf("## 절\n\n핵심은\n속도입니다. 파일을 엽니다. 표가 보입니다.\n", Config())
    assert baseline.keep("글.md", reflowed) == []


def testPruneDropsLocksThatAreGone():
    baseline, findings = lockOf(BAD)
    smaller = prune(baseline, {"글.md": findingsOf(FIXED, Config())})
    assert smaller.count < baseline.count
    assert prune(baseline, {"글.md": []}).count == 0


def testPruneLeavesFilesItDidNotSee():
    baseline = build({"하나.md": findingsOf(BAD, Config()), "둘.md": findingsOf(BAD, Config())})
    kept = prune(baseline, {"하나.md": []})
    assert "하나.md" not in kept.locked
    assert "둘.md" in kept.locked


def testRenderIsHumanReadableAndStable():
    baseline, _ = lockOf(BAD)
    text = render(baseline)
    data = json.loads(text)
    assert data["version"] == 1
    assert data["locked"] == baseline.count
    assert data["files"]["글.md"][0].keys() == {"rule", "quote"}
    assert render(parse(text)) == text


def testUnknownVersionIsRefused():
    with pytest.raises(ValueError, match="모르는 baseline 판"):
        parse(json.dumps({"version": 99, "files": {}}))


def testMissingFileSaysWhere(tmp_path):
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "없다.json")


def testPathKeyIsRelativeToTheLockFile(tmp_path, monkeypatch):
    """팀이 커밋해 함께 쓰는 파일이라 어떻게 쳤든 같은 키가 나와야 한다.

    절대 경로로 치든 다른 폴더에서 상대 경로로 치든 같은 글은 같은 키다. 이게 없으면 잠금 파일이
    만든 기계에서만 듣고 CI 에서는 아무것도 안 잠긴다.
    """
    target = tmp_path / ".hanlint-baseline.json"
    inside = tmp_path / "문서" / "글.md"
    inside.parent.mkdir()
    assert pathKey(str(inside), target) == "문서/글.md"
    monkeypatch.chdir(tmp_path)
    assert pathKey("문서/글.md", ".hanlint-baseline.json") == "문서/글.md"
    monkeypatch.chdir(inside.parent)
    assert pathKey("글.md", "../.hanlint-baseline.json") == "문서/글.md"
    assert pathKey("<stdin>", target) == "<stdin>"
    assert pathKey("아무거나", None) == "아무거나"
