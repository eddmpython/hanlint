"""`hanlint usage "낱말 …" --kind report --limit 5` 와 `hanlint usage build report 글폴더/`.

그 종류의 실제 글에서 질의의 낱말이 어떻게 쓰였는지를 문장으로 보인다. 색인은 사용자 기계 (`~/.cache/hanlint/usage/`)
에만 있고 `build` 가 만든다. 색인이 없으면 만드는 법을 알리고 2 로 끝난다. 좋은 문장을 고르지 않는다. BM25 순서로
쓰인 문장을 보이고 판정은 읽는 쪽이 한다. 뜻은 usage/sentences.py 가 소유한다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...config import USAGE_KINDS
from ...usage import Hit, buildIndex, defaultUsageRoot, loadIndex, readDocuments
from .shared import addOutputOption, emit

HELP = '그 종류의 실제 글에서 낱말이 쓰인 문장을 보인다 (usage "낱말"). 색인은 usage build <종류> <폴더> 가 만든다'
BUILD = "build"
DEFAULT_LIMIT = 5
DEFAULT_KIND = USAGE_KINDS[0]


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("targets", nargs="+", help="질의 낱말들. 첫 인자가 build 면 다음은 <종류> 와 <글 폴더> 다")
    parser.add_argument("--kind", default=DEFAULT_KIND, help=f"글의 종류. 기본 {DEFAULT_KIND}")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"보일 문장 수. 기본 {DEFAULT_LIMIT}")
    parser.add_argument("--root", type=Path, default=None, help="색인 폴더. 기본 ~/.cache/hanlint/usage")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="출력 꼴. 기본 text")
    addOutputOption(parser)


def missingIndex(kind: str) -> str:
    return (
        f"{kind} 색인이 없다. hanlint usage build {kind} <글 폴더> 로 만든다 (txt 와 md, 하위 폴더 포함). "
        "사업보고서는 scripts/fetch/dartReports.py 가 받는다"
    )


def renderText(kind: str, query: str, documents: int, sentences: int, hits: list[Hit]) -> str:
    lines = [f"{kind} 용례 (문서 {documents}편, 문장 {sentences}개): {query}"]
    if not hits:
        lines.append("쓰인 문장이 없다. 낱말을 줄이거나 다른 낱말로 묻는다")
    for number, hit in enumerate(hits, 1):
        lines.append(f"{number}. {hit.text}")
        lines.append(f"   문서 {hit.documents}편, 출처 {hit.source}")
    return "\n".join(lines)


def renderJson(kind: str, query: str, documents: int, sentences: int, hits: list[Hit]) -> str:
    data = {
        "version": 1,
        "kind": kind,
        "query": query,
        "documents": documents,
        "sentences": sentences,
        "hits": [{"text": hit.text, "documents": hit.documents, "source": hit.source, "score": hit.score} for hit in hits],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def run(args: argparse.Namespace) -> int:
    root = args.root or defaultUsageRoot()
    if args.targets[0] == BUILD:
        if len(args.targets) != 3:
            emit("hanlint usage build <종류> <글 폴더> 꼴로 준다", args.output)
            return 2
        kind, folder = args.targets[1], Path(args.targets[2])
        if not folder.is_dir():
            emit(f"{folder} 는 폴더가 아니다", args.output)
            return 2
        result = buildIndex(kind, readDocuments(folder), root)
        emit(
            f"{root / kind}: 문서 {result.documents}편, 문장 {result.sentences}개, 토큰 {result.terms}종. "
            f'hanlint usage "낱말" --kind {kind} 로 묻는다',
            args.output,
        )
        return 0
    query = " ".join(args.targets)
    index = loadIndex(args.kind, root)
    if index is None:
        emit(missingIndex(args.kind), args.output)
        return 2
    hits = index.search(query, max(args.limit, 0))
    render = renderJson if args.format == "json" else renderText
    emit(render(args.kind, query, index.documents, index.sentences, hits), args.output)
    return 0
