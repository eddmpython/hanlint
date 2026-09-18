"""`hanlint sheet 폴더/ --preset screen` 과 `hanlint sheet apply 시트.md`.

소스 파일 (js, jsx, mjs, cjs, ts, tsx, rs, py) 을 전부 뒤져 사람이 읽는 한국어 글을 표 하나로 떨군다. 기본은 지적이
있는 글만, `--all` 은 전부. 사람이 표의 `고침` 칸을 채우면 `apply` 가 그 자리를 파일에 되돌려 쓴다.

왜 있는가. 화면의 글은 수십 파일에 흩어져 있어 지적을 파일마다 받으면 전체가 안 보인다. 운영자가 표 하나로
모든 글을 보고 그 자리에서 고치게 한다 (2026-09-17, Taxly 화면 글 1,129건에서 왔다).
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePath

from ...config import Config
from ...document import SOURCE_SUFFIXES, replaceLiteral
from ...report import SheetRow, parseSheet, renderSheet, renderSheetJson, sheetRows
from .shared import addCommonOptions, configFrom, emit, isSkipped

HELP = "소스의 화면 글을 표 하나로 떨구거나 (sheet 폴더/), 고친 표를 파일로 되돌려 쓴다 (sheet apply 시트.md)"
APPLY = "apply"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("targets", nargs="+", help="소스 파일이나 폴더. 첫 인자가 apply 면 다음 인자는 고친 시트다")
    parser.add_argument("--all", dest="everything", action="store_true", help="지적이 없는 글도 표에 넣는다")
    parser.add_argument("--dry-run", dest="dryRun", action="store_true", help="apply 에서 파일을 쓰지 않고 무엇을 바꿀지만 본다")
    addCommonOptions(parser, ("markdown", "json"))


def sourceUnder(folder: Path) -> list[str]:
    """폴더 아래 소스 파일. 점 폴더와 node_modules 는 건너뛴다. 경로 문자열 순이라 두 판이 같은 차례를 낸다."""
    found: list[str] = []
    for child in sorted(folder.iterdir(), key=lambda p: p.name):
        if child.is_dir():
            if not isSkipped(child.name):
                found.extend(sourceUnder(child))
        elif child.suffix.lower() in SOURCE_SUFFIXES:
            found.append(str(child))
    # 구분자를 / 로 맞춘 뒤 정렬한다. \\ 는 / 보다 커서 Windows 와 다른 OS 의 순서가 갈리기 때문이다.
    return sorted(found, key=lambda item: PurePath(item).as_posix())


def collectSources(targets: list[str]) -> list[str]:
    found: list[str] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            found.extend(sourceUnder(path))
        elif path.exists():
            found.append(str(path))
        else:
            raise FileNotFoundError(target)
    return found


def relativeLabel(path: str) -> str:
    """작업 폴더 기준 상대 경로, 구분자는 `/`. 두 판이 같은 글자를 내야 한다."""
    try:
        return PurePath(Path(path).resolve().relative_to(Path.cwd().resolve())).as_posix()
    except ValueError:
        return PurePath(path).as_posix()


def buildRows(files: list[str], config: Config, everything: bool) -> list[SheetRow]:
    """디스크의 파일을 읽어 report.sheetRows 에 넘긴다. 행의 뜻은 그쪽이 소유한다."""
    return sheetRows(((relativeLabel(file), Path(file).read_text(encoding="utf-8")) for file in files), config, everything)


def replaceAt(lineText: str, column: int, old: str, new: str) -> tuple[str, bool]:
    """`column` (1부터) 에 `old` 가 그대로 있으면 그 자리만 `new` 로 바꾼다."""
    start = column - 1
    if start < 0 or lineText[start : start + len(old)] != old:
        return lineText, False
    return lineText[:start] + new + lineText[start + len(old) :], True


def applySheet(sheetPath: Path, dryRun: bool) -> tuple[list[str], list[str]]:
    """표의 고침을 파일에 쓴다. (적용한 자리, 실패한 자리와 이유).

    한 줄에 고침이 여럿이면 뒤 칸부터 바꾼다. 앞 칸을 먼저 바꾸면 길이가 달라져 뒤 칸의 자리가 어긋난다.
    """
    parsed = parseSheet(sheetPath.read_text(encoding="utf-8"))
    applied: list[str] = []
    failed: list[str] = list(parsed.problems)
    byFile: dict[str, list[SheetRow]] = {}
    for row in parsed.rows:
        byFile.setdefault(row.file, []).append(row)
    for file in sorted(byFile):
        path = Path(file)
        if not path.exists():
            failed.extend(f"{row.place}: 파일이 없다" for row in byFile[file])
            continue
        # newline="" 이라야 \r\n 이 \n 으로 바뀌지 않는다. npm 의 readFileSync 와 같이 줄 끝을 그대로 두고 그대로 쓴다.
        with path.open(encoding="utf-8", newline="") as handle:
            lines = handle.read().split("\n")
        changed = False
        for row in sorted(byFile[file], key=lambda row: (row.line, -row.column)):
            if row.line < 1 or row.line > len(lines):
                failed.append(f"{row.place}: 그 줄이 없다")
                continue
            if row.column > 0:
                newLine, hit = replaceAt(lines[row.line - 1], row.column, row.text, row.fix)
                if not hit:
                    failed.append(f"{row.place}: 그 칸에 그 글이 없다. 표를 다시 뽑는다")
                    continue
            else:
                newLine, count = replaceLiteral(lines[row.line - 1], row.text, row.fix)
                if count != 1:
                    failed.append(f"{row.place}: 글이 그 줄에 {count}번 있다. 한 번이어야 바꾼다")
                    continue
            lines[row.line - 1] = newLine
            changed = True
            applied.append(f"{row.place}: {row.text} -> {row.fix}")
        if changed and not dryRun:
            path.write_text("\n".join(lines), encoding="utf-8", newline="")
    return applied, failed


def run(args: argparse.Namespace) -> int:
    if args.targets[0] == APPLY:
        if len(args.targets) != 2:
            emit("hanlint sheet apply 시트.md 꼴로 시트 하나를 준다", args.output)
            return 2
        applied, failed = applySheet(Path(args.targets[1]), args.dryRun)
        lines = [f"{'볼 것' if args.dryRun else '적용'} {len(applied)}건, 실패 {len(failed)}건"]
        lines.extend(f"  {item}" for item in applied)
        lines.extend(f"  실패 {item}" for item in failed)
        emit("\n".join(lines), args.output)
        return 1 if failed else 0
    files = collectSources(args.targets)
    config = configFrom(args, start=Path(files[0]).resolve().parent if files else None)
    rows = buildRows(files, config, args.everything)
    if args.format == "json":
        emit(renderSheetJson(rows, config.preset, len(files)), args.output)
    else:
        emit(renderSheet(rows, config.preset, len(files)), args.output)
    return 0
