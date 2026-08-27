"""Write 와 Edit 앞에서 규칙 위반을 막는 Claude 훅.

무엇을 막나.
  - src, tests, hooks, scripts 아래 snake_case 파일 이름 (camelCase 가 강행규칙)
  - 쓰려는 내용의 em 대시 (U+2014) 와 en 대시 (U+2013)
  - 저장소 안 임시 산출물 경로 (dist, build, 캐시, 로그)

무엇을 못 막나. 식별자의 snake_case 는 파일 조각만 보는 훅이 오판하기 쉬워 tests/gates/testNaming.py
가 ast 로 본다. 이 훅은 쓰기 전에 잡을 수 있는 확실한 것만 잡는다.

판정은 순수 함수 `problemsIn` 이고 hooks/tests/checkWriteGate.py 가 양성과 음성으로 부른다.
페이로드를 못 읽으면 막지 않는다. 이것은 검사기이지 통행로가 아니다.
표준 라이브러리만 쓴다. python -X utf8 로 실행한다.
"""

from __future__ import annotations

import json
import re
import sys

CODE_DIRS = ("src/", "tests/", "hooks/", "scripts/")
PYTHON_EXCEPTIONS = {"__init__.py", "__main__.py", "conftest.py"}
DISPOSABLE = re.compile(
    r"(^|/)(dist|build|__pycache__|\.pytest_cache|\.ruff_cache|\.mypy_cache|node_modules)(/|$)|\.(log|pyc|tmp)$"
)
# 이스케이프로 적는다. 리터럴로 쓰면 이 파일이 자기 게이트와 pre-commit 에 걸린다.
DASHES = re.compile("[\u2013\u2014]")


def slash(value: object) -> str:
    return str(value or "").replace("\\", "/")


def repoRelative(path: str, projectDir: str) -> str | None:
    """저장소 안 경로면 루트 기준 상대 경로, 아니면 None."""
    path = slash(path)
    root = slash(projectDir).rstrip("/")
    if root and path.lower().startswith(root.lower() + "/"):
        return path[len(root) + 1 :]
    if not path.startswith("/") and not re.match(r"^[A-Za-z]:/", path):
        return path
    return None


def problemsIn(toolInput: dict, projectDir: str) -> list[str]:
    """쓰기 요청 하나의 문제 목록. 비어 있으면 통과."""
    problems: list[str] = []
    relative = repoRelative(toolInput.get("file_path") or toolInput.get("notebook_path") or "", projectDir)
    if relative is not None:
        if DISPOSABLE.search(relative):
            problems.append(f"저장소 안 임시 산출물 경로다. 공통 실행 공간으로 보낸다: {relative}")
        if relative.endswith(".py") and relative.startswith(CODE_DIRS):
            base = relative.rsplit("/", 1)[-1]
            if base not in PYTHON_EXCEPTIONS and "_" in base:
                problems.append(f"snake_case 파일 이름이다. camelCase 로 쓴다: {relative}")
    content = toolInput.get("content") or toolInput.get("new_string") or ""
    if DASHES.search(str(content)):
        problems.append("em 대시나 en 대시가 있다. 부연은 마침표로 끊고 범위는 물결표로 쓴다")
    return problems


def readPayload() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        return {}


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode != "pre":
        return 0
    payload = readPayload()
    projectDir = payload.get("cwd") or ""
    problems = problemsIn(payload.get("tool_input") or {}, projectDir)
    if not problems:
        return 0
    print("BLOCK: hanlint 규칙 위반 (operation.codeStyle)", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
