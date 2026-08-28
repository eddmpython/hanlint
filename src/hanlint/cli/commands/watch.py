"""`hanlint watch 글.md`. 파일이 바뀔 때마다 다시 검사한다.

글을 쓰는 사람은 저장하고, 터미널로 옮겨 가서, 명령을 다시 치고, 편집기로 돌아온다. 그 왕복이 검사를
안 돌리게 만든다. 편집기가 무엇이든 터미널 하나를 띄워 두면 되도록 이 명령이 그 자리를 메운다.

파이썬 쪽에만 있다 (audit, map, profile, coverage, diff 와 같다). 폴링으로 본다. 감시 라이브러리를
넣으면 런타임 의존성 0 이 깨지고, 글 몇 개를 보는 데 파일 시스템 이벤트까지는 필요하지 않다.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from ... import analyzerFor
from ...config import Config
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...report import renderCompact, renderText
from ...rules import Finding, runAll
from .shared import (
    addCommonOptions,
    addSeverityOptions,
    collectFiles,
    configFrom,
    fixableCount,
    header,
    keep,
    nextStep,
    readFile,
    severityOf,
    startFolder,
    summary,
)

HELP = "파일이 바뀔 때마다 다시 검사한다"
DEFAULT_INTERVAL = 0.5
"""초. 사람이 저장하고 눈을 드는 시간보다 짧으면 된다. 더 짧게 해도 얻는 것이 없다."""


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", help="지켜볼 마크다운 파일이나 폴더")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help=f"몇 초마다 보는가. 기본 {DEFAULT_INTERVAL}")
    addCommonOptions(parser, ("text", "compact"), output=False)
    addSeverityOptions(parser)


def stampOf(paths: list[str]) -> dict[str, float]:
    """경로 → 마지막 수정 시각. 사라진 파일은 빠진다. 이 사전이 바뀌면 다시 검사한다."""
    stamps: dict[str, float] = {}
    for path in paths:
        try:
            stamps[path] = Path(path).stat().st_mtime
        except OSError:
            continue
    return stamps


def report(paths: list[str], args: argparse.Namespace, config: Config) -> str:
    analyzer = analyzerFor(config)
    results: dict[str, list[Finding]] = {}
    texts: dict[str, str] = {}
    for path in paths:
        texts[path] = readFile(Path(path))
        doc = buildFingerprint(parseMarkdown(texts[path], path=path), analyzer, config)
        results[path] = runAll(doc, config)
    shown = {name: keep(found, severityOf(args)) for name, found in results.items()}
    if args.format == "compact":
        body = "\n".join(renderCompact(name, found) for name, found in shown.items() if found)
        parts = [body] if body else []
        parts.append(summary(results))
    else:
        parts = ["\n\n".join(renderText(name, found) for name, found in shown.items())]
        if len(shown) > 1:
            parts.append(summary(results))
    parts.append(nextStep(results, fixableCount(texts, results)))
    return "\n\n".join(parts) if args.format == "text" else "\n".join(parts)


def run(args: argparse.Namespace, rounds: int | None = None) -> int:
    """`rounds` 는 시험이 준다. None 이면 Ctrl+C 까지 돈다."""
    files = collectFiles(args.files)
    config = configFrom(args, start=startFolder(files))
    if not args.quiet:
        print(header(config))
        print(f"{len(files)}개를 지켜본다. 저장하면 다시 검사한다. 멈추려면 Ctrl+C")
    stamps: dict[str, float] = {}
    done = 0
    try:
        while rounds is None or done < rounds:
            current = stampOf(files)
            if current != stamps:
                stamps = current
                print(f"\n{'-' * 40}")
                print(report(files, args, config))
                done += 1
                continue
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n그만 본다")
    return 0
