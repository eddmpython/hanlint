"""`hanlint 글.md`. 검사하고 지적을 낸다. `--profile` 을 주면 참조 글과의 편차 구간을 notice 로 더한다."""

from __future__ import annotations

import argparse
from pathlib import Path

from ... import analyzerFor
from ...document import parseMarkdown
from ...fingerprint import DocumentPrint, buildFingerprint
from ...profile import Profile, compareToProfile, loadProfile
from ...report import renderGithub, renderJson, renderText
from ...rules import Finding, runAll
from ...rules.finding import DOCUMENT, NOTICE, SECTION
from .shared import addCommonOptions, configFrom, emit, readFile

HELP = "글을 검사한다. 서브커맨드 없이 파일만 줘도 된다"
PROFILE_RULE = "profile"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", type=Path, help="검사할 마크다운 파일")
    parser.add_argument("--profile", type=Path, help="hanlint profile build 가 만든 파일. 편차 구간을 notice 로 더한다")
    addCommonOptions(parser, ("text", "json", "github"))


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
    config = configFrom(args, start=args.files[0].resolve().parent)
    analyzer = analyzerFor(config)
    profilePath = args.profile or (Path(config.profile) if config.profile else None)
    profile = loadProfile(profilePath) if profilePath else None
    results = {}
    for path in args.files:
        doc = buildFingerprint(parseMarkdown(readFile(path), path=str(path)), analyzer, config)
        findings = runAll(doc, config)
        if profile:
            findings = sorted(findings + profileFindings(doc, profile), key=lambda f: (f.line, f.rule))
        results[str(path)] = findings

    if args.format == "json":
        emit(renderJson(results), args.output)
    elif args.format == "github":
        emit("\n".join(renderGithub(path, findings) for path, findings in results.items()), args.output)
    else:
        emit("\n\n".join(renderText(path, findings) for path, findings in results.items()), args.output)

    hasError = any(f.severity == "error" for findings in results.values() for f in findings)
    return 1 if hasError else 0
