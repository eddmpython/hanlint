"""이름 게이트. 파일과 폴더는 camelCase, 함수와 변수와 인자는 camelCase, 클래스는 PascalCase,
모듈 상수는 UPPER_SNAKE, 비공개는 _ 접두 camelCase.

정의 측만 본다. 호출 측 키워드 인자 (`json.dumps(x, ensure_ascii=False)`) 는 외부 계약이라 보지 않는다.
판정은 순수 함수 `namingViolations(source, path)` 와 `pathViolation(path)` 이고 fixture 로 양방향을 증명한다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CODE_DIRS = ("src", "tests", "hooks", "scripts")
PATH_EXCEPTIONS = {"__init__.py", "conftest.py"}

CAMEL = re.compile(r"^_?[a-z][a-zA-Z0-9]*$")
PASCAL = re.compile(r"^_?[A-Z][a-zA-Z0-9]*$")
UPPER_SNAKE = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
DUNDER = re.compile(r"^__\w+__$")


def pathViolation(relativePath: str) -> str | None:
    """`src/hanlint/parse_markdown.py` 같은 저장소 상대 경로가 규칙에 맞는가."""
    parts = relativePath.replace("\\", "/").split("/")
    if parts[0] not in CODE_DIRS:
        return None
    for folder in parts[1:-1]:
        if not CAMEL.match(folder):
            return f"폴더 이름이 camelCase 가 아니다: {relativePath}"
    base = parts[-1]
    if not base.endswith(".py") or base in PATH_EXCEPTIONS:
        return None
    if not CAMEL.match(base[:-3]):
        return f"파일 이름이 camelCase 가 아니다: {relativePath}"
    return None


def identifierViolations(name: str, kind: str) -> str | None:
    if DUNDER.match(name) or name == "_":
        return None
    if kind == "class":
        return None if PASCAL.match(name) else f"클래스 {name} 은 PascalCase 다"
    if kind == "constant":
        return None if UPPER_SNAKE.match(name) or CAMEL.match(name) else f"모듈 상수 {name} 은 UPPER_SNAKE 다"
    return None if CAMEL.match(name) else f"{kind} {name} 은 camelCase 다"


def namingViolations(source: str, path: str = "<source>") -> list[str]:
    tree = ast.parse(source)
    violations: list[str] = []

    def report(problem: str | None, line: int) -> None:
        if problem:
            violations.append(f"{path}:{line} {problem}")

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            report(identifierViolations(node.name, "class"), node.lineno)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            report(identifierViolations(node.name, "함수"), node.lineno)
            for arg in node.args.args + node.args.kwonlyargs + node.args.posonlyargs:
                report(identifierViolations(arg.arg, "인자"), arg.lineno)
            if node.args.vararg:
                report(identifierViolations(node.args.vararg.arg, "인자"), node.lineno)
            if node.args.kwarg:
                report(identifierViolations(node.args.kwarg.arg, "인자"), node.lineno)
    # 모듈 수준 대입은 상수 후보, 함수 안 대입은 변수.
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            for target in [node.target] if isinstance(node, ast.AnnAssign) else node.targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        report(identifierViolations(name.id, "constant"), node.lineno)
    for func in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for node in ast.walk(func):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
                for target in targets:
                    for name in ast.walk(target):
                        if isinstance(name, ast.Name):
                            report(identifierViolations(name.id, "변수"), node.lineno)
    return violations


def codeFiles() -> list[Path]:
    files: list[Path] = []
    for folder in CODE_DIRS:
        base = ROOT / folder
        if base.exists():
            files.extend(p for p in base.rglob("*.py") if ".venv" not in p.parts)
    return files


def testRealTreePathsAreCamelCase():
    problems = [pathViolation(p.relative_to(ROOT).as_posix()) for p in codeFiles()]
    assert [p for p in problems if p] == []


def testRealTreeIdentifiersFollowRules():
    files = codeFiles()
    if not files:
        pytest.skip("검사할 파이썬 파일이 없다")
    problems: list[str] = []
    for path in files:
        problems.extend(namingViolations(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix()))
    assert problems == []


def testSparesCamelPascalUpperAndPrivate():
    source = (
        "NOUN_TAGS = {'NNG'}\n"
        "_sharedAnalyzer = None\n"
        "class SentencePrint:\n    pass\n"
        "def lintText(text, config=None, *rest, **options):\n"
        "    startLine = 1\n    _hidden = 2\n    return startLine\n"
        "def __call__(self):\n    return self\n"
    )
    assert namingViolations(source) == []


def testCatchesSnakeFunctionArgAndVariable():
    source = "def lint_text(raw_text):\n    start_line = 1\n    return start_line\n"
    problems = namingViolations(source, "x.py")
    assert [p.split(" ", 1)[1] for p in problems] == [
        "함수 lint_text 은 camelCase 다",
        "인자 raw_text 은 camelCase 다",
        "변수 start_line 은 camelCase 다",
    ]


def testCatchesLowerClassAndSnakeConstant():
    assert namingViolations("class sentence_print:\n    pass\n") == [
        "<source>:1 클래스 sentence_print 은 PascalCase 다"
    ]
    assert namingViolations("noun_tags = 1\n") == ["<source>:1 모듈 상수 noun_tags 은 UPPER_SNAKE 다"]


def testSparesCallSiteKeywords():
    source = "import json\ndef dump(value):\n    return json.dumps(value, ensure_ascii=False)\n"
    assert namingViolations(source) == []


def testPathRules():
    assert pathViolation("src/hanlint/parseMarkdown.py") is None
    assert pathViolation("src/hanlint/__init__.py") is None
    assert pathViolation("tests/conftest.py") is None
    assert pathViolation("docs/some_note.md") is None
    assert (
        pathViolation("src/hanlint/parse_markdown.py")
        == "파일 이름이 camelCase 가 아니다: src/hanlint/parse_markdown.py"
    )
    assert (
        pathViolation("src/hanlint/rules/sentence_rules/x.py")
        == "폴더 이름이 camelCase 가 아니다: src/hanlint/rules/sentence_rules/x.py"
    )
    assert pathViolation("tests/rules/test_deixis.py") is not None
