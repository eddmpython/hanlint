"""명령들이 함께 쓰는 인자와 준비."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ...config import Config, loadConfig
from ...rules import Finding

FORMATS = ("text", "json", "github", "html", "compact")
SEVERITIES = ("all", "error", "notice")
STDIN = "-"
STDIN_NAME = "<stdin>"


def addCommonOptions(parser: argparse.ArgumentParser, formats: tuple[str, ...] = ("text", "json")) -> None:
    parser.add_argument("--config", type=Path, help="설정 파일. 없으면 hanlint.toml 이나 pyproject.toml 을 찾는다")
    parser.add_argument(
        "--disable", action="append", default=[], metavar="RULE", help="이번 실행에서 끌 규칙. 여러 번 줄 수 있다"
    )
    parser.add_argument("--analyzer", choices=("surface", "kiwi"), help="분석기. 기본은 설정이나 surface")
    parser.add_argument("--format", choices=formats, default=formats[0], help=f"출력 꼴. 기본 {formats[0]}")
    parser.add_argument("--output", type=Path, help="출력을 파일로 쓴다")
    parser.add_argument("--no-color", dest="noColor", action="store_true", help="색을 끈다")
    parser.add_argument("--quiet", action="store_true", help="설정 출처 줄을 뺀다")


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


def isStdin(path: Path | str) -> bool:
    return str(path) == STDIN


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
