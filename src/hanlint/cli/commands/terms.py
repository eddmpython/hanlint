"""`hanlint terms 글.md`. 한국어 학습자에게 처음 풀어 쓸 낱말 후보.

국립국어원 한국어 학습용 어휘 C에만 등재된 화제어의 첫 자리를 낸다. 한국어 모어 화자의 난도나 글의
등급을 판정하지 않는다. `--outside`는 목록 밖 한글 화제어도 후보로 보이지만 전문어와 고유명사를 가르지
않는다.
"""

from __future__ import annotations

import argparse
import json

from ...data.learningVocabulary import Term, termsIn, vocabularyMetadata
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from .shared import addCommonOptions, collectFiles, configFrom, emit, readInput, startFolder

HELP = "한국어 학습자에게 처음 풀어 쓸 낱말 후보를 찾는다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", help="살필 마크다운 파일. `-`는 stdin")
    parser.add_argument("--path", dest="stdinPath", default="<stdin>", help="stdin으로 넣은 글의 이름")
    parser.add_argument("--outside", action="store_true", help="학습용 어휘 목록 밖 한글 화제어 후보도 보인다")
    addCommonOptions(parser, ("text", "json"))


def termReason(term: Term) -> str:
    if term.outside:
        return "학습용 어휘 목록 밖 화제어 후보다. 전문어와 고유명사를 가르지 않으므로 처음 풀어 쓸지는 문맥으로 정한다"
    return "한국어 학습용 어휘 목록에서 C에만 등재된 화제어다. 한국어 학습자를 위한 글이면 처음 나올 때 풀어 쓸지 확인한다"


def renderTermsText(results: dict[str, tuple[Term, ...]], includeOutside: bool) -> str:
    blocks: list[str] = []
    for path, terms in results.items():
        graded = sum(1 for term in terms if not term.outside)
        outside = sum(1 for term in terms if term.outside)
        summary = f"{path}  C 전용 화제어 {graded}개"
        if includeOutside:
            summary += f", 목록 밖 후보 {outside}개"
        lines = [summary]
        for term in terms:
            label = "목록 밖" if term.outside else "/".join(term.grades)
            lines.extend(["", f"{path}:{term.line}  [{label}] {term.word}", f"  {termReason(term)}"])
        blocks.append("\n".join(lines))
    title = vocabularyMetadata()["dataset"]["title"]
    return f"자료: {title}\n\n" + "\n\n".join(blocks)


def renderTermsJson(results: dict[str, tuple[Term, ...]]) -> str:
    dataset = vocabularyMetadata()["dataset"]
    data = {
        "version": 1,
        "source": {
            "title": dataset["title"],
            "url": dataset["sourceUrl"],
            "license": dataset["license"],
        },
        "files": [{"path": path, "terms": [term.asDict() for term in terms]} for path, terms in results.items()],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def run(args: argparse.Namespace) -> int:
    files = collectFiles(args.files)
    config = configFrom(args, start=startFolder(files))
    results: dict[str, tuple[Term, ...]] = {}
    for path in files:
        name, text = readInput(path, args.stdinPath)
        document = buildFingerprint(parseMarkdown(text, path=name), config)
        results[name] = termsIn(document, args.outside)
    rendered = renderTermsJson(results) if args.format == "json" else renderTermsText(results, args.outside)
    emit(rendered, args.output)
    return 0
