"""`hanlint 글.md`. 검사하고 지적을 낸다.

`-` 는 stdin 이고 `--path` 가 그 이름이다. `--severity` 와 `--errors-only` 가 보여 줄 지적을 고르고
`--format compact` 가 한 줄에 지적 하나를 낸다. `--profile` 을 주면 참조 글과의 편차 구간을 notice 로 더한다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ... import analyzerFor
from ...baseline import DEFAULT_NAME, Baseline, load
from ...document import parseMarkdown
from ...fingerprint import DocumentPrint, buildFingerprint
from ...profile import Profile, compareToProfile, loadProfile
from ...report import renderCompact, renderGithub, renderJson, renderText
from ...rules import Finding, runAll
from ...rules.finding import DOCUMENT, NOTICE, SECTION
from .shared import (
    STDIN_NAME,
    addCommonOptions,
    addSeverityOptions,
    collectFiles,
    configFrom,
    configLabel,
    emit,
    header,
    keep,
    nextStep,
    readInput,
    severityOf,
    startFolder,
    summary,
)

HELP = "글을 검사한다. 서브커맨드 없이 파일만 줘도 된다"
PROFILE_RULE = "profile"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", help="검사할 마크다운 파일. `-` 는 stdin")
    parser.add_argument("--path", dest="stdinPath", default=STDIN_NAME, help="stdin 으로 넣은 글의 이름")
    parser.add_argument("--profile", type=Path, help="hanlint profile build 가 만든 파일. 편차 구간을 notice 로 더한다")
    parser.add_argument(
        "--baseline",
        nargs="?",
        const=DEFAULT_NAME,
        type=Path,
        help=f"잠근 지적을 적은 파일. 그 안의 것은 넘긴다. 값을 안 주면 {DEFAULT_NAME}",
    )
    addCommonOptions(parser, ("text", "compact", "json", "github"))
    addSeverityOptions(parser)


def profileFindings(doc: DocumentPrint, profile: Profile) -> list[Finding]:
    """편차를 notice 지적으로 옮긴다. 규칙 이름은 profile 하나다."""
    findings = []
    for deviation in compareToProfile(doc, profile):
        if deviation.scope == "section":
            quote = doc.sections[deviation.index].title or "도입"
            findings.append(
                Finding(PROFILE_RULE, deviation.line, quote, deviation.describe(), None, NOTICE, SECTION, deviation.index)
            )
        else:
            findings.append(
                Finding(PROFILE_RULE, deviation.line, doc.path or "글 전체", deviation.describe(), None, NOTICE, DOCUMENT)
            )
    return findings


def run(args: argparse.Namespace) -> int:
    files = collectFiles(args.files)
    config = configFrom(args, start=startFolder(files))
    analyzer = analyzerFor(config)
    profilePath = args.profile or (Path(config.profile) if config.profile else None)
    profile = loadProfile(profilePath) if profilePath else None
    baselinePath = args.baseline or (Path(config.baseline) if config.baseline else None)
    baseline = load(baselinePath) if baselinePath else Baseline()
    results: dict[str, list[Finding]] = {}
    for path in files:
        name, text = readInput(path, args.stdinPath)
        doc = buildFingerprint(parseMarkdown(text, path=name), analyzer, config)
        findings = runAll(doc, config)
        if profile:
            findings = sorted(findings + profileFindings(doc, profile), key=lambda f: (f.line, f.rule))
        results[name] = baseline.keep(name, findings)

    hasError = any(f.severity == "error" for findings in results.values() for f in findings)
    severity = severityOf(args)
    shown = {name: keep(findings, severity) for name, findings in results.items()}

    if args.format == "json":
        emit(renderJson(shown, configLabel=configLabel(config)), args.output)
    elif args.format == "github":
        emit("\n".join(renderGithub(name, findings) for name, findings in shown.items()), args.output)
    else:
        parts: list[str] = []
        if not args.quiet:
            parts.append(header(config))
        if args.format == "compact":
            body = "\n".join(renderCompact(name, findings) for name, findings in shown.items() if findings)
            if body:
                parts.append(body)
            parts.append(summary(shown))
        else:
            parts.append("\n\n".join(renderText(name, findings) for name, findings in shown.items()))
            if len(shown) > 1:
                parts.append(summary(shown))
        if not args.quiet:
            if baseline.count:
                parts.append(f"잠근 자리 {baseline.count}건은 넘겼다 ({baseline.source}). 그 문장을 고치면 다시 나온다")
            parts.append(nextStep(shown))
        emit("\n\n".join(parts) if args.format == "text" else "\n".join(parts), args.output)
    return 1 if hasError else 0
