"""`hanlint profile build 글들/`. 승인된 글들의 지문 분포를 profile.json 으로 만든다.

견주는 것은 lint 의 `--profile` 이다. 설정의 profile 키로도 준다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ... import analyzerFor
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...profile import buildProfile, saveProfile
from .shared import configFrom, readFile

HELP = "승인된 글들의 지문 분포를 만든다"


def addParser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="profileCommand", required=True)
    build = sub.add_parser("build", help="폴더 안 마크다운 전부에서 프로파일을 만든다")
    build.add_argument("folder", type=Path, help="승인된 글이 있는 폴더. 하위 폴더까지 본다")
    build.add_argument("--output", type=Path, default=Path("profile.json"), help="쓸 파일. 기본 profile.json")
    build.add_argument("--config", type=Path, help="설정 파일")
    build.add_argument("--analyzer", choices=("surface", "kiwi"))


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=args.folder.resolve())
    analyzer = analyzerFor(config)
    files = sorted(args.folder.rglob("*.md"))
    if not files:
        raise ValueError(f"{args.folder} 에 마크다운 파일이 없다")
    docs = [buildFingerprint(parseMarkdown(readFile(path), path=str(path)), analyzer, config) for path in files]
    profile = buildProfile(docs)
    saveProfile(profile, args.output)
    print(f"{args.output} 에 글 {profile.documentCount}편의 분포를 썼다. hanlint 글.md --profile {args.output} 로 견준다")
    return 0
