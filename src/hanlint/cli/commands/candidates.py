"""`hanlint candidates 글.md`. 지적마다 말뭉치가 뒷받침하는 고침 후보를 닫힌 목록으로 낸다.

무엇을 쓸지 짓지 않는다. 그 종류의 실제 글이 그 자리에 쓴 조사만 모아 원문에 넣어 보고, 겨눈 규칙이 풀리고 error 가
늘지 않는 꼴만 남긴다. 어느 후보가 뜻에 맞는지는 고르는 쪽 (사람이나 LLM) 이 정한다. 등수도 점수도 없다.

문장 색인이 있어야 돈다 (`hanlint usage build <종류> <폴더>`). 없으면 만드는 법을 알리고 2 로 끝난다.
뜻은 edit/usageCandidates.py 가 소유한다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...edit import MAX_CANDIDATES, usageCandidates
from ...usage import defaultUsageRoot, listIndexes, loadIndex, usageKindOf
from .shared import addCommonOptions, collectFiles, configFrom, emit, readInput, startFolder

HELP = "지적마다 말뭉치가 뒷받침하는 고침 후보를 낸다. 색인은 usage build <종류> <폴더> 가 만든다"
FORMAT_VERSION = 1


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", help="검사할 마크다운 파일. `-` 는 stdin")
    parser.add_argument("--root", type=Path, default=None, help="색인 폴더. 기본 ~/.cache/hanlint/usage")
    parser.add_argument("--limit", type=int, default=MAX_CANDIDATES, help=f"지적 하나에 낼 후보 수. 기본 {MAX_CANDIDATES}")
    addCommonOptions(parser, ("text", "json"))


def missingIndex(kind: str | None, root: Path) -> str:
    if kind is None:
        return "글의 종류가 정해지지 않았다. --preset report 를 주거나 설정에 usageKind 를 적는다"
    kinds = ", ".join(str(meta["kind"]) for meta in listIndexes(root)) or "없음"
    return f"{kind} 색인이 없다 (있는 것: {kinds}). hanlint usage build {kind} <글 폴더> 로 만든다"


def textOf(name: str, findings: list) -> list[str]:
    lines = [f"# {name}"]
    for finding in findings:
        lines.append("")
        lines.append(f"{finding.line}:{finding.rule}  {finding.why}")
        lines.append(f"  원문  {' '.join(finding.quote.split())}")
        for candidate in finding.candidates:
            lines.append(f"  후보  {' '.join(candidate.text.split())}")
            lines.append(f"        {candidate.why}")
    if len(lines) == 1:
        lines.append("")
        lines.append("말뭉치가 뒷받침하는 후보가 붙은 지적이 없다")
    return lines


def run(args: argparse.Namespace) -> int:
    files = collectFiles(args.files)
    config = configFrom(args, start=startFolder(files))
    root = args.root or defaultUsageRoot()
    kind = usageKindOf(config)
    index = loadIndex(kind, root) if kind else None
    if index is None:
        print(missingIndex(kind, root))
        return 2

    results = {}
    for path in files:
        name, text = readInput(path, getattr(args, "stdinPath", "<stdin>"))
        results[name] = usageCandidates(text, config, index=index, limit=args.limit)

    if args.format == "json":
        payload = {
            "version": FORMAT_VERSION,
            "kind": index.kind,
            "documents": index.documents,
            "files": {
                name: [
                    {
                        "rule": finding.rule,
                        "line": finding.line,
                        "why": finding.why,
                        "quote": finding.quote,
                        "candidates": [candidate.asDict() for candidate in finding.candidates],
                    }
                    for finding in findings
                ]
                for name, findings in results.items()
            },
        }
        emit(json.dumps(payload, ensure_ascii=False, indent=2), args.output)
    else:
        emit("\n".join(line for name, findings in results.items() for line in textOf(name, findings)), args.output)
    return 0
