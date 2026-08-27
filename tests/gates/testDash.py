"""em 대시와 en 대시 게이트. git 이 추적하는 텍스트 파일 전체를 본다.

이스케이프 문자열 (`"\\u2014"`) 은 실제 문자가 아니라 통과한다. 판정은 순수 함수 `dashLines(text)`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {".py", ".md", ".toml", ".json", ".txt", ".sh", ".yml", ".yaml"}
DASHES = ("\u2014", "\u2013")


def dashLines(text: str) -> list[int]:
    """대시가 있는 줄 번호 (1 부터)."""
    return [number for number, line in enumerate(text.splitlines(), start=1) if any(d in line for d in DASHES)]


def trackedTextFiles() -> list[Path]:
    output = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    files = []
    for line in output.splitlines():
        path = ROOT / line.strip()
        if path.suffix in TEXT_SUFFIXES or line.startswith(".githooks/"):
            files.append(path)
    return files


def testTrackedFilesHaveNoDashes():
    problems = []
    for path in trackedTextFiles():
        if not path.exists():
            continue
        for number in dashLines(path.read_text(encoding="utf-8")):
            problems.append(f"{path.relative_to(ROOT).as_posix()}:{number}")
    assert problems == []


def testCatchesBothDashes():
    assert dashLines("빠르다 \u2014 그리고\n범위 2020\u20132024\n") == [1, 2]


def testSparesHyphenTildeAndEscapes():
    assert dashLines('a-b 2020~2024 EM = "\\u2014"\n') == []
