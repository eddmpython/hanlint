"""명령들이 함께 쓰는 인자와 준비."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ...config import Config, loadConfig
from ...data import patternsAvoiding
from ...rules import Finding

FORMATS = ("text", "json", "github", "html", "compact")
SEVERITIES = ("all", "error", "notice")
STDIN = "-"
STDIN_NAME = "<stdin>"
MARKDOWN = (".md", ".markdown")
"""폴더를 주면 이 확장자만 찾는다. 글 폴더에 섞여 있는 이미지와 설정을 검사하지 않는다."""


def addCommonOptions(parser: argparse.ArgumentParser, formats: tuple[str, ...] = ("text", "json"), output: bool = True) -> None:
    """설정과 출력 꼴 옵션. `output` 은 그 명령이 실제로 파일로 쓸 수 있을 때만 켠다.

    받아 놓고 안 쓰는 옵션은 거짓말이다. 특히 `--output` 은 조용히 무시되면 사용자가 기다리던 파일이
    안 생긴다 (실측: rules, doctor, fix, watch 넷이 그랬다). 그래서 emit 을 부르는 명령만 받는다.
    `--no-color` 는 아직 색이 없는 출력에서도 받는다. 스크립트가 관례로 붙이는 것을 막을 이유가 없고
    무시돼도 잃는 것이 없다.
    """
    parser.add_argument("--config", type=Path, help="설정 파일. 없으면 hanlint.toml 이나 pyproject.toml 을 찾는다")
    parser.add_argument(
        "--disable", action="append", default=[], metavar="RULE", help="이번 실행에서 끌 규칙. 여러 번 줄 수 있다"
    )
    parser.add_argument("--analyzer", choices=("surface", "kiwi"), help="분석기. 기본은 설정이나 surface")
    parser.add_argument("--format", choices=formats, default=formats[0], help=f"출력 꼴. 기본 {formats[0]}")
    if output:
        addOutputOption(parser)
    parser.add_argument("--no-color", dest="noColor", action="store_true", help="색을 끈다")
    parser.add_argument("--quiet", action="store_true", help="설정 출처 줄을 뺀다")


def addOutputOption(parser: argparse.ArgumentParser) -> None:
    """`--output`. 이 옵션을 받는 명령은 반드시 `emit` 으로 그 값을 쓴다."""
    parser.add_argument("--output", type=Path, help="출력을 파일로 쓴다")


def addSeverityOptions(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--severity", choices=SEVERITIES, default="all", help="보여 줄 지적. 기본 all")
    parser.add_argument("--errors-only", dest="errorsOnly", action="store_true", help="--severity error 와 같다")


def severityOf(args: argparse.Namespace) -> str:
    if getattr(args, "errorsOnly", False):
        return "error"
    return getattr(args, "severity", "all")


def keep(findings: list[Finding], severity: str) -> list[Finding]:
    if severity == "all":
        return findings
    return [f for f in findings if f.severity == severity]


def configFrom(args: argparse.Namespace, start: Path | None = None) -> Config:
    config = loadConfig(args.config, start=start)
    config.disable |= set(getattr(args, "disable", []) or [])
    if getattr(args, "analyzer", None):
        config.analyzer = args.analyzer
    return config


def configLabel(config: Config) -> str:
    """출력 첫 줄에 적을 설정 출처. 현재 폴더 아래면 상대 경로, 아니면 그대로."""
    if config.source is None:
        return "기본값"
    try:
        relative = os.path.relpath(config.source)
    except ValueError:
        return config.source
    return config.source if relative.startswith("..") else relative


def header(config: Config) -> str:
    return f"설정: {configLabel(config)}"


def summary(results: dict[str, list[Finding]]) -> str:
    errors = sum(1 for findings in results.values() for f in findings if f.severity == "error")
    notices = sum(1 for findings in results.values() for f in findings if f.severity == "notice")
    return f"파일 {len(results)}개, error {errors}, notice {notices}"


def nextStep(results: dict[str, list[Finding]]) -> str:
    """검사 끝에 붙는 다음 행동 한 줄. 합격을 판정하지 않고 지금 무엇을 하면 되는지만 말한다."""
    findings = [f for found in results.values() for f in found]
    errors = [f for f in findings if f.severity == "error"]
    notices = len(findings) - len(errors)
    fixable = sum(1 for f in errors if f.replacement is not None)
    if errors:
        rule = sorted({f.rule for f in errors})[0]
        if fixable:
            return f"다음: error {len(errors)}건 가운데 {fixable}건은 hanlint fix 가 바로 고친다. 나머지는 손으로 고친다"
        if patternsAvoiding(rule):
            return f"다음: error {len(errors)}건을 고친다. 다시 쓸 틀은 hanlint patterns --rule {rule}"
        return f"다음: error {len(errors)}건을 고친다. 규칙이 왜 있는지는 hanlint explain {rule}"
    if notices:
        return f"다음: error 0. 확인할 자리 {notices}건을 읽고 판단한 뒤 사람과 LLM 평가로 넘어간다"
    return "다음: 세어서 잡히는 결함이 없다. 좋은 글이라는 뜻은 아니므로 사람과 LLM 평가로 넘어간다"


def isStdin(path: Path | str) -> bool:
    return str(path) == STDIN


def collectFiles(paths: list) -> list[str]:
    """폴더를 주면 그 아래 마크다운을 이름 순으로 편다. 파일과 `-` 는 그대로 둔다."""
    found: list[str] = []
    for path in paths:
        if isStdin(path):
            found.append(STDIN)
            continue
        candidate = Path(path)
        if candidate.is_dir():
            # 경로 문자열로 정렬한다. Path 끼리의 비교는 윈도에서 대소문자를 무시해 npm 판과 갈린다.
            inside = sorted((p for p in candidate.rglob("*") if p.suffix.lower() in MARKDOWN and p.is_file()), key=str)
            if not inside:
                raise ValueError(f"{path} 안에 마크다운 파일이 없다. 다른 폴더를 주거나 파일을 직접 준다")
            found.extend(str(p) for p in inside)
            continue
        found.append(str(path))
    return found


def readInput(path: Path | str, stdinName: str = STDIN_NAME) -> tuple[str, str]:
    """(이름, 본문). `-` 면 stdin 을 UTF-8 로 읽는다."""
    if isStdin(path):
        return stdinName, sys.stdin.buffer.read().decode("utf-8")
    return str(path), readFile(Path(path))


def startFolder(paths: list) -> Path:
    """설정을 찾기 시작할 폴더. 첫 실제 파일의 폴더, 전부 stdin 이면 현재 폴더."""
    for path in paths:
        if not isStdin(path):
            return Path(path).resolve().parent
    return Path.cwd()


def readFile(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def emit(text: str, output: Path | None) -> None:
    if output is None:
        print(text)
        return
    output.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    print(f"{output} 에 썼다", file=sys.stderr)


def colorEnabled(args: argparse.Namespace) -> bool:
    if getattr(args, "noColor", False) or getattr(args, "output", None) is not None:
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())
