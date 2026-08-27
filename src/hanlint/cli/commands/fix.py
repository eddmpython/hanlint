"""`hanlint fix 글.md`. 기계가 고칠 수 있는 지적을 원문에 적용한다.

바꾼 자리와 건너뛴 자리를 줄마다 보여 준다. `--dry-run` 은 파일을 바꾸지 않고 무엇을 바꿀지만 보여 준다.
줄 끝 (LF, CRLF) 은 원문 그대로 둔다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ... import analyzerFor
from ...document import parseMarkdown
from ...edit import applyFixes
from ...fingerprint import buildFingerprint
from ...rules import runAll
from .shared import addCommonOptions, collectFiles, configFrom, startFolder

HELP = "기계가 고칠 수 있는 지적을 원문에 적용한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", help="고칠 마크다운 파일이나 폴더")
    parser.add_argument("--dry-run", dest="dryRun", action="store_true", help="파일을 바꾸지 않고 무엇을 바꿀지만 보여 준다")
    addCommonOptions(parser, ("text",))


def readRaw(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def writeRaw(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def run(args: argparse.Namespace) -> int:
    files = collectFiles(args.files)
    config = configFrom(args, start=startFolder(files))
    analyzer = analyzerFor(config)
    lines: list[str] = []
    for path in files:
        text = readRaw(Path(path))
        doc = buildFingerprint(parseMarkdown(text, path=path), analyzer, config)
        # notice 는 제안이라 손으로 정한다. 확정된 error 만 원문에 넣는다.
        result = applyFixes(text, [f for f in runAll(doc, config) if f.severity == "error"])
        for line, fragment, replacement in result.applied:
            lines.append(f"{path}:{line}  {fragment} → {replacement}")
        for line, fragment, reason in result.skipped:
            lines.append(f"{path}:{line}  건너뜀 {fragment}: {reason}")
        if result.text != text and not args.dryRun:
            writeRaw(Path(path), result.text)
        lines.append(
            f"{path}  {len(result.applied)}곳 고침, {len(result.skipped)}곳 건너뜀"
            + (" (미리보기, 파일은 그대로)" if args.dryRun else "")
        )
    print("\n".join(lines))
    return 0
