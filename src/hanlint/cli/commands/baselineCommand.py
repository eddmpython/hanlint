"""`hanlint baseline 글들/`. 지금 있는 지적을 잠가 두고 새로 생긴 것만 막게 한다.

이미 쓴 글이 많은 저장소에 도구를 들일 때 쓴다. 실측: 남의 저장소 문서 여섯 편에 그냥 돌리면 error 가
25건 나오고, 첫날 그것을 보는 팀은 도구를 끈다. 규칙이 틀린 것이 아니라 첫날 양이 문제다.

잠금은 줄 번호가 아니라 인용문으로 건다. 그래서 문장이 자리만 옮기면 잠긴 채고, **고치면 새 지적이 된다.**
손댔으면 책임진다. 기한도 비율도 없이 글을 고칠 때마다 잠금이 줄어든다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ...baseline import DEFAULT_NAME, build, load, prune, render
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...rules import Finding, runAll
from .shared import addCommonOptions, collectFiles, configFrom, emit, readInput, startFolder

HELP = "지금 있는 지적을 잠근다. 그다음부터 새로 생긴 것만 막힌다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", help="잠글 마크다운 파일이나 폴더")
    parser.add_argument("--prune", action="store_true", help="글에 더 없는 잠금을 지운다. 이미 있는 파일을 읽어 줄인다")
    addCommonOptions(parser, ("text",))


def findingsOf(files: list[str], config) -> dict[str, list[Finding]]:
    results: dict[str, list[Finding]] = {}
    for path in files:
        name, text = readInput(path)
        results[name] = runAll(buildFingerprint(parseMarkdown(text, path=name), config), config)
    return results


def run(args: argparse.Namespace) -> int:
    files = collectFiles(args.files)
    config = configFrom(args, start=startFolder(files))
    target = args.output or Path(config.baseline or DEFAULT_NAME)
    results = findingsOf(files, config)
    baseline = prune(load(target), results) if args.prune else build(results, target)
    # 팀이 커밋해 함께 쓰는 파일이라 줄끝을 LF 로 고정한다. 윈도의 기본 변환이면 두 판의 파일이 달라진다
    target.write_text(render(baseline) + "\n", encoding="utf-8", newline="\n")
    what = "잠금을 줄였다" if args.prune else "지적을 잠갔다"
    emit(
        f"{baseline.source} 에 {baseline.count}건을 적었다. {len(files)}개 글의 {what}.\n"
        "다음: 검사할 때 --baseline 을 붙이거나 설정에 baseline 을 적는다. 잠긴 자리를 고치면 새 지적으로 다시 나온다",
        None,
    )
    return 0
