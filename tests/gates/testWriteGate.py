"""hooks/writeGate.py 의 양성과 음성. 막아야 할 것과 막지 말아야 할 것을 짝으로 본다.

판정은 순수 함수 `problemsIn` 이고 실제 실행은 stdin 페이로드와 종료 코드로 본다. 페이로드를 못 읽으면 막지
않는다. 검사기이지 통행로가 아니다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from hooks.writeGate import problemsIn

ROOT = "C:/repo/hanlint"
GATE = Path(__file__).resolve().parents[2] / "hooks" / "writeGate.py"

BLOCKED = {
    "snake 파일 src": {"file_path": f"{ROOT}/src/hanlint/parse_markdown.py", "content": ""},
    "snake 파일 tests": {"file_path": f"{ROOT}/tests/rules/test_deixis.py", "content": ""},
    "snake 파일 상대경로": {"file_path": "scripts/commit_message.py", "content": ""},
    "역슬래시 경로": {"file_path": "C:\\repo\\hanlint\\hooks\\write_gate.py", "content": ""},
    "em 대시 내용": {"file_path": f"{ROOT}/README.md", "content": "빠르다 \u2014 그리고"},
    "en 대시 edit": {"file_path": f"{ROOT}/README.md", "new_string": "2020\u20132024"},
    "임시 산출물 dist": {"file_path": f"{ROOT}/dist/out.txt", "content": "x"},
    "임시 산출물 로그": {"file_path": f"{ROOT}/run.log", "content": "x"},
    "snake 파일 npm js": {"file_path": f"{ROOT}/npm/src/document/parse_markdown.js", "content": ""},
    "snake 파일 web js": {"file_path": f"{ROOT}/web/engine_client.js", "content": ""},
    "snake 파일 mjs": {"file_path": f"{ROOT}/scripts/measure/site_check.mjs", "content": ""},
    "npm node_modules": {"file_path": f"{ROOT}/npm/node_modules/x/index.js", "content": ""},
    "임시 산출물 build": {"file_path": f"{ROOT}/build/lib/x.py", "content": "x"},
    "임시 산출물 pycache": {"file_path": f"{ROOT}/src/hanlint/__pycache__/x.pyc", "content": "x"},
    "임시 산출물 pytest 캐시": {"file_path": f"{ROOT}/.pytest_cache/v/x", "content": "x"},
    "임시 산출물 ruff 캐시": {"file_path": f"{ROOT}/.ruff_cache/x", "content": "x"},
    "임시 산출물 mypy 캐시": {"file_path": f"{ROOT}/.mypy_cache/x", "content": "x"},
    "임시 산출물 pyc": {"file_path": f"{ROOT}/src/hanlint/x.pyc", "content": "x"},
    "임시 산출물 tmp": {"file_path": f"{ROOT}/notes.tmp", "content": "x"},
    "소문자 드라이브 snake": {"file_path": "c:/repo/hanlint/src/hanlint/a_b.py", "content": ""},
}
"""막아야 할 쓰기 요청."""

SPARED = {
    "camel 파일": {"file_path": f"{ROOT}/src/hanlint/parseMarkdown.py", "content": ""},
    "__init__": {"file_path": f"{ROOT}/src/hanlint/__init__.py", "content": ""},
    "conftest": {"file_path": f"{ROOT}/tests/conftest.py", "content": ""},
    "__main__": {"file_path": f"{ROOT}/src/hanlint/__main__.py", "content": ""},
    "camel js": {"file_path": f"{ROOT}/npm/src/document/parseMarkdown.js", "content": ""},
    "camel web js": {"file_path": f"{ROOT}/web/engineClient.js", "content": ""},
    "camel mjs": {"file_path": f"{ROOT}/scripts/measure/siteCheck.mjs", "content": ""},
    "node test 파일": {"file_path": f"{ROOT}/npm/test/rules.test.js", "content": ""},
    "코드 폴더 밖 snake": {"file_path": f"{ROOT}/docs/some_note.md", "content": ""},
    "저장소 밖 snake": {"file_path": "C:/Users/someone/AppData/Local/dev-workspace/x/scratch_file.py", "content": ""},
    "물결표와 하이픈": {"file_path": f"{ROOT}/README.md", "content": "2020~2024 a-b"},
    "dash 이스케이프 문자열": {"file_path": f"{ROOT}/src/hanlint/x.py", "content": 'EM = "\\u2014"'},
    "빈 입력": {},
}
"""막지 말아야 할 쓰기 요청."""


@pytest.mark.parametrize("name", sorted(BLOCKED))
def testBlocks(name: str) -> None:
    assert problemsIn(BLOCKED[name], ROOT), name


@pytest.mark.parametrize("name", sorted(SPARED))
def testSpares(name: str) -> None:
    assert problemsIn(SPARED[name], ROOT) == [], name


def run(mode: str, payload: str) -> int:
    """훅을 실제로 실행한 종료 코드. 2 가 차단이다."""
    done = subprocess.run(
        [sys.executable, "-X", "utf8", str(GATE), mode],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return done.returncode


def testRunBlocksSnakeFile() -> None:
    payload = json.dumps({"cwd": ROOT, "tool_input": {"file_path": f"{ROOT}/src/a_b.py", "content": ""}})
    assert run("pre", payload) == 2


def testRunPassesCamelFile() -> None:
    payload = json.dumps({"cwd": ROOT, "tool_input": {"file_path": f"{ROOT}/src/aB.py", "content": ""}})
    assert run("pre", payload) == 0


def testRunPassesBrokenPayload() -> None:
    assert run("pre", "not json") == 0


def testRunIgnoresOtherMode() -> None:
    assert run("post", "{}") == 0
