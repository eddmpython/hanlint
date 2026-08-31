"""README 의 명령 표가 실제 두 판의 명령 목록과 맞는지 본다.

README 는 명령마다 npm 칸에 예 또는 아니오 를 적는다. 이 게이트가 그 칸을 실제 실행으로 확인하므로
표는 손으로 관리하는 문장이 아니라 검사되는 투영이다.

2026-08-31 이전에는 파이썬 전용이라는 사실을 줄 끝 문구와 표 아래 문장이 나눠 들고 있었고, 열넷 가운데
넷만 적혀 있었다. npx 사용자가 문서대로 `hanlint learn` 을 치면 안내와 함께 2 로 끝났다.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
NODE = shutil.which("node")
ROW = re.compile(r"^\| `hanlint(?: ([a-z][a-z-]*))?[^|]*\|[^|]*\| (예|아니오) \|$")


def tableRows() -> list[tuple[str, bool]]:
    """(명령, npm 에 있나). 명령 낱말이 없는 줄은 lint 의 꼴이다."""
    rows = []
    for line in README.read_text(encoding="utf-8").split("\n"):
        match = ROW.match(line.rstrip())
        if match:
            rows.append((match.group(1) or "lint", match.group(2) == "예"))
    return rows


def testTableCoversEveryPythonCommand():
    commands = {path.stem for path in (ROOT / "src" / "hanlint" / "cli" / "commands").glob("*.py")}
    commands -= {"__init__", "shared"}
    # 파일 이름이 명령 이름과 다른 셋. 파이썬 예약어와 겹쳐 뒤에 Command 를 붙였다.
    renamed = {"baselineCommand": "baseline", "mapCommand": "map", "patternsCommand": "patterns", "printFingerprint": "print"}
    commands = {renamed.get(name, name) for name in commands}
    listed = {command for command, _ in tableRows()}
    assert not commands - listed, f"README 명령 표에 없는 명령: {sorted(commands - listed)}"


@pytest.mark.skipif(NODE is None, reason="node 가 없다")
def testNpmColumnMatchesNpmCli():
    rows = tableRows()
    assert len(rows) > 20, f"명령 표를 못 읽었다 ({len(rows)}줄)"
    wrong = []
    for command, claimed in sorted({(command, claimed) for command, claimed in rows}):
        if command == "lint":
            continue
        done = subprocess.run(
            [NODE, str(ROOT / "npm" / "bin" / "hanlint.js"), command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )
        # 파이썬 전용 명령은 무엇을 대신 쓰라는 안내와 함께 2 로 끝난다.
        missing = done.returncode == 2 and "파이썬 패키지에 있다" in (done.stdout + done.stderr)
        if claimed == missing:
            wrong.append(f"{command}: README 는 npm {'있다' if claimed else '없다'} 라는데 실제는 반대다")
    assert not wrong, "\n".join(wrong)
