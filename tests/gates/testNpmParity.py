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
    python, node = runBoth(["explain", "doublePassive"])
    assert python.stdout == node.stdout
