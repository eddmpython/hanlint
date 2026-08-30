"""`hanlint learn 전.md 후.md`. 실제 고침에서 승인할 정확 패치와 표면 치환 후보를 찾는다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...learn import LearnedExemplar, LearnedOperation, learnExemplars, learnOperations
from ...rules import runAll
from .shared import addCommonOptions, configFrom, emit, readFile, startFolder

HELP = "두 초안에서 사람이 승인할 패치 후보를 찾는다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("before", type=Path, help="앞선 초안")
    parser.add_argument("after", type=Path, help="고친 초안")
    addCommonOptions(parser, ("text", "json", "toml"))


def flat(text: str) -> str:
    return " ".join(text.split())


def lineLabel(lines: tuple[int, ...]) -> str:
    if len(lines) == 1:
        return f"{lines[0]}줄"
    return f"{lines[0]}-{lines[-1]}줄"


def renderLearnText(
    candidates: tuple[LearnedExemplar, ...],
    operations: tuple[LearnedOperation, ...],
    beforePath: Path,
    afterPath: Path,
) -> str:
    lines = [f"패치 후보 {len(candidates)}건, 표면 연산 후보 {len(operations)}건  {beforePath} -> {afterPath}"]
    if not candidates and not operations:
        lines.append("사라진 문장 지적이나 안전한 일대일 표면 치환이 없거나 문장 대응이 모호하다")
        return "\n".join(lines)
    lines.append("사람이 뜻을 확인하고 적용 범위를 정한 뒤 hanlint.toml 에 승인한다")
    for candidate in candidates:
        lines.extend(
            [
                "",
                f"[{candidate.rule}] 전 {candidate.beforeLine}줄 -> 후 {lineLabel(candidate.afterLines)}",
                f"  전  {flat(candidate.before)}",
                f"  후  {flat(candidate.after)}",
                f"  사라진 까닭: {flat(candidate.why)}",
                f"  선택 조건: cue={candidate.cue!r}, reader={candidate.reader}, presets={','.join(candidate.presets)}",
            ]
        )
    for operation in operations:
        first = operation.evidence[0]
        lines.extend(
            [
                "",
                f"[surfaceSubstitution] {operation.before!r} -> {operation.after!r}",
                f"  증거 {len(operation.evidence)}건, 첫 자리 전 {first.beforeLine}줄 -> 후 {first.afterLine}줄",
                f"  전  {flat(first.sourceBefore)}",
                f"  후  {flat(first.sourceAfter)}",
                "  가드: 32자 이하, 표면 편집 거리 1 이하, 단어 경계 한 자리, 숫자·코드·링크 보존",
            ]
        )
    return "\n".join(lines)


def renderLearnJson(
    candidates: tuple[LearnedExemplar, ...],
    operations: tuple[LearnedOperation, ...],
    beforePath: Path,
    afterPath: Path,
) -> str:
    data = {
        "version": 1,
        "beforePath": str(beforePath),
        "afterPath": str(afterPath),
        "candidates": [candidate.asDict() for candidate in candidates],
        "operations": [operation.asDict() for operation in operations],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def tomlString(text: str) -> str:
    """한 줄 TOML 기본 문자열. JSON 문자열의 이스케이프는 이 범위에서 TOML 과 같다."""
    return json.dumps(flat(text), ensure_ascii=False)


def renderLearnToml(candidates: tuple[LearnedExemplar, ...], operations: tuple[LearnedOperation, ...]) -> str:
    lines = ["# hanlint learn 후보. 문장 대응과 뜻을 확인한 뒤 승인한다."]
    for candidate in candidates:
        presets = ", ".join(tomlString(preset) for preset in candidate.presets)
        lines.extend(
            [
                "",
                f"# 전 {candidate.beforeLine}줄 -> 후 {lineLabel(candidate.afterLines)}. {flat(candidate.why)}",
                "[[patches]]",
                f"rule = {tomlString(candidate.rule)}",
                f"before = {tomlString(candidate.before)}",
                f"after = {tomlString(candidate.after)}",
                f"moved = {tomlString(candidate.moved)}",
                f"sourceText = {tomlString(candidate.before)}",
                f"sentence = {tomlString(candidate.sentence)}",
                f"cue = {tomlString(candidate.cue)}",
                f"reader = {tomlString(candidate.reader)}",
            ]
        )
        if candidate.presets:
            lines.append(f"presets = [{presets}]")
    for operation in operations:
        presets = ", ".join(tomlString(preset) for preset in operation.presets)
        first = operation.evidence[0]
        lines.extend(
            [
                "",
                f"# 증거 {len(operation.evidence)}건. 첫 자리 전 {first.beforeLine}줄 -> 후 {first.afterLine}줄.",
                "# 뜻이 같고 이 낱말의 다른 원문에도 적용해도 되는지 확인한 뒤 승인한다.",
                "[[operations]]",
                f"before = {tomlString(operation.before)}",
                f"after = {tomlString(operation.after)}",
            ]
        )
        if operation.presets:
            lines.append(f"presets = [{presets}]")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=startFolder([args.after]))
    beforeDoc = buildFingerprint(parseMarkdown(readFile(args.before), path=str(args.before)), config)
    afterDoc = buildFingerprint(parseMarkdown(readFile(args.after), path=str(args.after)), config)
    candidates = learnExemplars(
        beforeDoc,
        afterDoc,
        runAll(beforeDoc, config),
        runAll(afterDoc, config),
        config.preset,
    )
    operations = learnOperations(beforeDoc, afterDoc, config.preset, config.protectedTerms)
    if args.format == "json":
        rendered = renderLearnJson(candidates, operations, args.before, args.after)
    elif args.format == "toml":
        rendered = renderLearnToml(candidates, operations)
    else:
        rendered = renderLearnText(candidates, operations, args.before, args.after)
    emit(rendered, args.output)
    return 0
