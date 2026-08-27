"""npm 구현이 파이썬과 같은 결과를 내는지. 두 CLI 에 같은 파일들을 주고 JSON 과 text 출력을 글자 단위로 견준다.

입력은 모든 fixture 의 catch 와 spare, README, skills 문서다. node 가 없으면 건너뛰고 그 사실을 말한다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import expandTokens

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "rules"
NODE_CLI = ROOT / "npm" / "bin" / "hanlint.js"
NODE = shutil.which("node")


def sampleTexts() -> list[str]:
    texts = []
    for path in sorted(FIXTURES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("config"):
            continue
        texts.extend(expandTokens(text) for text in data["catch"] + data["spare"])
    return texts


def runBoth(args: list[str]) -> tuple[subprocess.CompletedProcess, subprocess.CompletedProcess]:
    python = subprocess.run(
        [sys.executable, "-X", "utf8", "-B", "-m", "hanlint", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    node = subprocess.run(
        [str(NODE), str(NODE_CLI), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    return python, node


CHUNK = 40
"""한 호출에 넘기는 파일 수. 윈도의 명령줄 한계 (32767자) 아래를 유지한다. v0.0.4 의 publish 게이트가
CI 윈도에서 파일 전체 나열로 WinError 206 을 냈다. 두 구현을 같은 청크로 돌리므로 동등성 판정은 같다."""


@pytest.mark.skipif(NODE is None, reason="node 가 없다. npm 동등성은 node 가 있는 기계에서 본다")
def testBothClisGiveTheSameOutput(tmp_path):
    files = []
    for index, text in enumerate(sampleTexts()):
        path = tmp_path / f"s{index:03}.md"
        path.write_text(text, encoding="utf-8")
        files.append(str(path))
    files.extend(str(p) for p in [ROOT / "README.md", *sorted((ROOT / "skills").rglob("*.md"))])

    formats = (["--format", "json"], ["--format", "text", "--no-color"], ["--format", "compact", "--errors-only"])
    for start in range(0, len(files), CHUNK):
        chunk = files[start : start + CHUNK]
        for extra in formats:
            python, node = runBoth([*chunk, *extra])
            assert python.returncode == node.returncode, node.stderr
            assert python.stdout == node.stdout

    for layer in ("all", "paragraphs"):
        python, node = runBoth(["print", str(ROOT / "README.md"), "--layer", layer])
        assert python.returncode == node.returncode == 0, node.stderr
        assert python.stdout == node.stdout


@pytest.mark.skipif(NODE is None, reason="node 가 없다")
def testFixPreviewAgrees(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(
        "## 절\n\n모든 분야에 있어서 기준이 필요합니다. 파일을 확인하세" + "요. 노력하지 않으면 안 됩니다.\n\n"
        "`에 있어서` 는 번역투입니다. 분야에 있어서 기준과 방식에 있어서 차이가 있습니다.\n",
        encoding="utf-8",
    )
    python, node = runBoth(["fix", str(draft), "--dry-run"])
    assert python.returncode == node.returncode == 0, node.stderr
    assert python.stdout == node.stdout
    assert "3곳 고침, 2곳 건너뜀" in python.stdout


@pytest.mark.skipif(NODE is None, reason="node 가 없다")
def testRuleListsAgree():
    python, node = runBoth(["rules", "--names"])
    assert python.stdout == node.stdout
    for rule in ("doublePassive", "moreLater", "numberOrphan"):
        python, node = runBoth(["explain", rule])
        assert python.stdout == node.stdout, rule
    python, node = runBoth(["explain"])
    assert python.returncode == node.returncode == 2
    assert python.stdout == node.stdout
    python, node = runBoth(["explain", "doublePasive"])
    assert python.returncode == node.returncode == 2
    assert "doubleNegative, doublePassive" in node.stderr

    # 기계가 읽는 꼴. 에이전트가 규칙과 본보기와 틀을 한 덩어리로 받는 자리라 두 판이 같아야 한다.
    for args in (["rules", "--format", "json"], ["explain", "nounPile", "--format", "json"]):
        python, node = runBoth(args)
        assert python.returncode == node.returncode == 0, node.stderr
        assert python.stdout == node.stdout, args


@pytest.mark.skipif(NODE is None, reason="node 가 없다")
def testEntryPointsAgree(tmp_path):
    """진입점 셋. 인자 없는 첫 화면, 폴더 인자, 부류로 묶은 규칙 목록."""
    python, node = runBoth([])
    assert python.returncode == node.returncode == 0, node.stderr
    assert python.stdout == node.stdout

    folder = tmp_path / "글들"
    (folder / "안").mkdir(parents=True)
    (folder / "하나.md").write_text("## 절\n\n핵심은 속도입니다.\n", encoding="utf-8")
    (folder / "안" / "둘.md").write_text("## 절\n\n파일을 엽니다.\n", encoding="utf-8")
    for extra in (["--format", "compact"], ["--format", "text", "--no-color"]):
        python, node = runBoth([str(folder), *extra])
        assert python.returncode == node.returncode, node.stderr
        assert python.stdout == node.stdout

    python, node = runBoth(["rules"])
    assert python.stdout == node.stdout

    for extra in ([], ["--rule", "nounPile"], ["--format", "json"]):
        python, node = runBoth(["patterns", *extra])
        assert python.returncode == node.returncode == 0, node.stderr
        assert python.stdout == node.stdout, extra


@pytest.mark.skipif(NODE is None, reason="node 가 없다")
def testInitPresetsAgree(tmp_path):
    # 같은 경로에 두 판을 쓰면 뒤 것이 `이미 있다` 로 막히므로 경로를 나눠 쓰고 내용을 견준다.
    for preset in ("blog", "report", "docs"):
        pythonPath = tmp_path / f"{preset}Python.toml"
        nodePath = tmp_path / f"{preset}Node.toml"
        python = subprocess.run(
            [sys.executable, "-X", "utf8", "-B", "-m", "hanlint", "init", "--output", str(pythonPath), "--preset", preset],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        node = subprocess.run(
            [str(NODE), str(NODE_CLI), "init", "--output", str(nodePath), "--preset", preset],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        assert python.returncode == 0, python.stderr
        assert node.returncode == 0, node.stderr
        assert pythonPath.read_text(encoding="utf-8") == nodePath.read_text(encoding="utf-8"), preset
        assert python.stdout.replace(str(pythonPath), "") == node.stdout.replace(str(nodePath), ""), preset


@pytest.mark.skipif(NODE is None, reason="node 가 없다")
def testBaselineAgrees(tmp_path):
    """잠금 파일은 팀이 커밋해 두 판이 함께 읽는 파일이라 글자까지 같아야 한다."""
    folder = tmp_path / "글들"
    folder.mkdir()
    (folder / "하나.md").write_text("## 절\n\n핵심은 속도입니다. 파일을 엽니다.\n", encoding="utf-8")
    (folder / "둘.md").write_text("## 절\n\n결국 중요한 것은 노력입니다. 표가 보입니다.\n", encoding="utf-8")

    pythonLock = tmp_path / "python.json"
    nodeLock = tmp_path / "node.json"

    def lockBoth(extra):
        python, _ = runBoth(["baseline", str(folder), *extra, "--output", str(pythonLock)])
        node = subprocess.run(
            [str(NODE), str(NODE_CLI), "baseline", str(folder), *extra, "--output", str(nodeLock)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        assert python.returncode == node.returncode == 0, node.stderr
        assert pythonLock.read_bytes() == nodeLock.read_bytes()
        assert python.stdout.replace(str(pythonLock), "") == node.stdout.replace(str(nodeLock), "")

    lockBoth([])
    for extra in (["--format", "compact"], ["--format", "text", "--no-color"], ["--format", "json"]):
        python, node = runBoth([str(folder), "--baseline", str(pythonLock), *extra])
        assert python.returncode == node.returncode == 0, node.stderr
        assert python.stdout == node.stdout, extra

    # 잠긴 문장을 고치면 두 판 모두 새 지적으로 낸다. 잠금이 새 결함을 감추지 않는다는 계약이다.
    (folder / "하나.md").write_text("## 절\n\n핵심은 그저 속도입니다. 파일을 엽니다.\n", encoding="utf-8")
    python, node = runBoth([str(folder), "--baseline", str(pythonLock), "--format", "compact"])
    assert python.returncode == node.returncode == 1, node.stderr
    assert python.stdout == node.stdout

    lockBoth(["--prune"])
