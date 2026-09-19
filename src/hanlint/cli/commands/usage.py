"""`hanlint usage "낱말 …" --kind report --limit 5`, `hanlint usage build <종류> <글 폴더>`, `hanlint usage kinds`.

그 종류의 실제 글에서 질의의 낱말이 어떻게 쓰였는지를 보인다. 먼저 낱말마다 함께 쓰는 말 (바로 뒤의 용언, 뒤와 앞의
명사, 문서 수) 을, 그다음 BM25 순서로 문장을 문서 수와 출처와 함께 낸다. 색인은 사용자 기계 (`~/.cache/hanlint/usage/`)
에만 있고 `build` 가 만든다 (txt, md, jsonl). 색인이 없으면 만드는 법을 알리고 2 로 끝난다. 좋은 문장을 고르지 않는다.
뜻은 usage/sentences.py 가 소유한다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...config import USAGE_KINDS
from ...usage import Collocation, Hit, buildIndex, defaultUsageRoot, listIndexes, loadIndex, queryCores, readDocuments
from .shared import addOutputOption, emit

HELP = '그 종류의 실제 글에서 낱말이 함께 쓰는 말과 쓰인 문장을 보인다 (usage "낱말"). 색인은 usage build <종류> <폴더>'
BUILD = "build"
KINDS = "kinds"
DEFAULT_LIMIT = 5
DEFAULT_KIND = USAGE_KINDS[0]
QUERY_WORDS = 3
"""함께 쓰는 말을 낼 낱말 수 상한. 질의 앞에서부터."""


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "targets", nargs="+", help="질의 낱말들. build <종류> <글 폴더> 는 색인을 만들고, kinds 는 있는 색인을 센다"
    )
    parser.add_argument("--kind", default=DEFAULT_KIND, help=f"글의 종류. 기본 {DEFAULT_KIND}")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"보일 문장 수. 기본 {DEFAULT_LIMIT}")
    parser.add_argument("--root", type=Path, default=None, help="색인 폴더. 기본 ~/.cache/hanlint/usage")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="출력 꼴. 기본 text")
    addOutputOption(parser)


def missingIndex(kind: str, root: Path) -> str:
    kinds = ", ".join(str(meta["kind"]) for meta in listIndexes(root)) or "없음"
    return (
        f"{kind} 색인이 없다 (있는 것: {kinds}). hanlint usage build {kind} <글 폴더> 로 만든다 (txt, md, jsonl. 하위 폴더 "
        "포함). 사업보고서는 scripts/fetch/dartReports.py, 위키백과는 scripts/fetch/koWikipedia.py 가 받는다"
    )


def pairText(items: tuple[tuple[str, int], ...]) -> str:
    return ", ".join(f"{term} {count}편" for term, count in items)


def informative(item: Collocation | None) -> bool:
    return item is not None and bool(item.predicates or item.following or item.preceding)


def renderText(
    kind: str, query: str, documents: int, sentences: int, wordsUsed: list[Collocation], hits: list[Hit], limit: int
) -> str:
    lines = [f"{kind} 용례 (문서 {documents}편, 문장 {sentences}개): {query}"]
    for item in wordsUsed:
        lines.append(f"함께 쓰는 말 ({item.term}, 문장 {item.sampled}개에서)")
        for label, pairs in (("뒤 용언", item.predicates), ("뒤 명사", item.following), ("앞 명사", item.preceding)):
            if pairs:
                lines.append(f"   {label}: {pairText(pairs)}")
    if not hits and limit > 0:
        lines.append("쓰인 문장이 없다. 낱말을 줄이거나 다른 낱말로 묻는다")
    for number, hit in enumerate(hits, 1):
        lines.append(f"{number}. {hit.text}")
        lines.append(f"   문서 {hit.documents}편, 출처 {hit.source}")
    return "\n".join(lines)


def renderJson(kind: str, query: str, documents: int, sentences: int, wordsUsed: list[Collocation], hits: list[Hit]) -> str:
    data = {
        "version": 2,
        "kind": kind,
        "query": query,
        "documents": documents,
        "sentences": sentences,
        "words": [
            {
                "term": item.term,
                "sampled": item.sampled,
                "predicates": [[term, count] for term, count in item.predicates],
                "following": [[term, count] for term, count in item.following],
                "preceding": [[term, count] for term, count in item.preceding],
            }
            for item in wordsUsed
        ],
        "hits": [{"text": hit.text, "documents": hit.documents, "source": hit.source, "score": hit.score} for hit in hits],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def renderKinds(root: Path, asJson: bool) -> str:
    found = listIndexes(root)
    if asJson:
        return json.dumps({"version": 1, "root": str(root), "kinds": found}, ensure_ascii=False, indent=2)
    if not found:
        return f"{root} 에 색인이 없다. hanlint usage build <종류> <글 폴더> 로 만든다"
    lines = [f"색인 {len(found)}개 ({root})"]
    for meta in found:
        lines.append(f"  {meta['kind']}: 문서 {meta['documents']}편, 문장 {meta['sentences']}개, 토큰 {meta['terms']}종")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    root = args.root or defaultUsageRoot()
    if args.targets[0] == KINDS:
        emit(renderKinds(root, args.format == "json"), args.output)
        return 0
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
        emit(missingIndex(args.kind, root), args.output)
        return 2
    limit = max(args.limit, 0)
    wordsUsed = [item for item in (index.collocations(core) for core in queryCores(query)[:QUERY_WORDS]) if informative(item)]
    hits = index.search(query, limit)
    if args.format == "json":
        emit(renderJson(args.kind, query, index.documents, index.sentences, wordsUsed, hits), args.output)
    else:
        emit(renderText(args.kind, query, index.documents, index.sentences, wordsUsed, hits, limit), args.output)
    return 0
