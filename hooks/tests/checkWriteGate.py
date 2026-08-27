"""writeGate.py 의 자기 검사. 막아야 할 것과 막지 말아야 할 것을 같은 수로 본다.

python -X utf8 hooks/tests/checkWriteGate.py 로 돈다. 실패하면 1 로 끝난다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from writeGate import problemsIn  # noqa: E402

ROOT = "C:/repo/hanlint"
failed = 0


def check(name: str, actual: object, expected: object) -> None:
    global failed
    if actual != expected:
        failed += 1
        print(f"  FAIL {name}\n    기대 {expected!r}\n    실제 {actual!r}", file=sys.stderr)


def blocked(toolInput: dict) -> bool:
    return bool(problemsIn(toolInput, ROOT))


# 막아야 할 것
check("snake 파일 src", blocked({"file_path": f"{ROOT}/src/hanlint/parse_markdown.py", "content": ""}), True)
check("snake 파일 tests", blocked({"file_path": f"{ROOT}/tests/rules/test_deixis.py", "content": ""}), True)
check("snake 파일 상대경로", blocked({"file_path": "scripts/commit_message.py", "content": ""}), True)
check("역슬래시 경로", blocked({"file_path": "C:\\repo\\hanlint\\hooks\\write_gate.py", "content": ""}), True)
check("em 대시 내용", blocked({"file_path": f"{ROOT}/README.md", "content": "빠르다 \u2014 그리고"}), True)
check("en 대시 edit", blocked({"file_path": f"{ROOT}/README.md", "new_string": "2020\u20132024"}), True)
check("임시 산출물 dist", blocked({"file_path": f"{ROOT}/dist/out.txt", "content": "x"}), True)
check("임시 산출물 로그", blocked({"file_path": f"{ROOT}/run.log", "content": "x"}), True)

# 막지 말아야 할 것
check("camel 파일", blocked({"file_path": f"{ROOT}/src/hanlint/parseMarkdown.py", "content": ""}), False)
check("__init__", blocked({"file_path": f"{ROOT}/src/hanlint/__init__.py", "content": ""}), False)
check("conftest", blocked({"file_path": f"{ROOT}/tests/conftest.py", "content": ""}), False)
check("코드 폴더 밖 snake", blocked({"file_path": f"{ROOT}/docs/some_note.md", "content": ""}), False)
check(
    "저장소 밖 snake",
    blocked({"file_path": "C:/Users/MSI/AppData/Local/dev-workspace/x/scratch_file.py", "content": ""}),
    False,
)
check("물결표와 하이픈", blocked({"file_path": f"{ROOT}/README.md", "content": "2020~2024 a-b"}), False)
check(
    "dash 이스케이프 문자열",
    blocked({"file_path": f"{ROOT}/src/hanlint/x.py", "content": 'EM = "\\u2014"'}),
    False,
)
check("빈 입력", blocked({}), False)

# 실제 실행. 페이로드를 stdin 으로 넣고 종료 코드를 본다.
gate = HERE.parent / "writeGate.py"


def run(payload: dict) -> int:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(gate), "pre"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).returncode


check(
    "실행: snake 차단",
    run({"cwd": ROOT, "tool_input": {"file_path": f"{ROOT}/src/a_b.py", "content": ""}}),
    2,
)
check("실행: camel 통과", run({"cwd": ROOT, "tool_input": {"file_path": f"{ROOT}/src/aB.py", "content": ""}}), 0)
check(
    "실행: 깨진 페이로드는 통과",
    subprocess.run([sys.executable, "-X", "utf8", str(gate), "pre"], input="not json", capture_output=True, text=True).returncode,
    0,
)
check(
    "실행: 다른 모드는 통과",
    run({"cwd": ROOT, "tool_input": {"file_path": f"{ROOT}/src/a_b.py"}})
    if False
    else subprocess.run([sys.executable, "-X", "utf8", str(gate), "post"], input="{}", capture_output=True, text=True).returncode,
    0,
)

if failed:
    print(f"\nwriteGate 자기 검사 {failed}건 실패", file=sys.stderr)
    sys.exit(1)
print("writeGate 자기 검사 통과")
