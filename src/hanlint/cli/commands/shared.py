"""명령들이 함께 쓰는 인자와 준비."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ...config import Config, loadConfig

FORMATS = ("text", "json", "github", "html")


def addCommonOptions(parser: argparse.ArgumentParser, formats: tuple[str, ...] = ("text", "json")) -> None:
    parser.add_argument("--config", type=Path, help="설정 파일. 없으면 hanlint.toml 이나 pyproject.toml 을 찾는다")
    parser.add_argument(
        "--disable", action="append", default=[], metavar="RULE", help="이번 실행에서 끌 규칙. 여러 번 줄 수 있다"
    )
    parser.add_argument("--analyzer", choices=("surface", "kiwi"), help="분석기. 기본은 설정이나 surface")
    parser.add_argument("--format", choices=formats, default=formats[0], help=f"출력 꼴. 기본 {formats[0]}")
    parser.add_argument("--output", type=Path, help="출력을 파일로 쓴다")
    parser.add_argument("--no-color", dest="noColor", action="store_true", help="색을 끈다")


def configFrom(args: argparse.Namespace, start: Path | None = None) -> Config:
    config = loadConfig(args.config, start=start)
    config.disable |= set(getattr(args, "disable", []) or [])
    if getattr(args, "analyzer", None):
        config.analyzer = args.analyzer
    return config


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
