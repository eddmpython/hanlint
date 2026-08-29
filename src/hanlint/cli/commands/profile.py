"""`hanlint profile build 글들/`. 참조 글들의 분포를 profile.json 으로 만든다.

견주는 것은 lint 의 `--profile` (설정의 profile 키) 이다. 그 파일이 있으면 규칙 outsideProfile 이 종류의 프로파일
대신 그것과 견준다. 파일의 꼴은 hanlint 가 싣는 종류별 프로파일 (data/profiles.json) 과 같다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ...data.profiles import saveProfile
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...profile import buildProfile
from .shared import configFrom, readFile

HELP = "참조 글들의 지문 분포를 만든다"


def addParser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="profileCommand", required=True)
    build = sub.add_parser("build", help="폴더 안 마크다운 전부에서 프로파일을 만든다")
    build.add_argument("folder", type=Path, help="참조 글이 있는 폴더. 하위 폴더까지 본다")
    build.add_argument("--output", type=Path, default=Path("profile.json"), help="쓸 파일. 기본 profile.json")
    build.add_argument("--config", type=Path, help="설정 파일")


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=args.folder.resolve())
    files = sorted(path for path in args.folder.rglob("*.md") if path.is_file())
    if not files:
        raise ValueError(f"{args.folder} 에 마크다운 파일이 없다")
    docs = [buildFingerprint(parseMarkdown(readFile(path), path=str(path)), config) for path in files]
    profile = buildProfile(docs)
    saveProfile(profile, args.output)
    print(
        f"{args.output} 에 글 {profile.documents}편, 문장 {profile.sentences}개의 분포를 썼다. "
        f"hanlint 글.md --profile {args.output} 로 견준다"
    )
    return 0
