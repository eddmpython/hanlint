from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule
from ..shared import codeBlocksOf

QUOTED = r"\(\s*[\"']([^\"'\n]+)[\"']"
READS = re.compile(
    r"\b(?:read_csv|read_excel|read_parquet|read_json|read_sql|read_table|read_ndjson|scan_csv|scan_parquet|scan_ndjson|"
    r"read_text|read_bytes|loadtxt|imread|load_workbook)" + QUOTED
)
OPENS = re.compile(r"\bopen" + QUOTED + r"\s*(?:,\s*(?:mode\s*=\s*)?[\"']([^\"']*)[\"'])?")
WRITES = re.compile(
    r"\b(?:to_csv|to_excel|to_parquet|to_json|to_sql|write_csv|write_parquet|write_json|write_ndjson|sink_parquet|sink_csv|"
    r"write_text|write_bytes|savefig|save|imwrite|savetxt|dump)" + QUOTED
)
SHELL_WRITES = re.compile(r"(?:>>?|-o|-O|--output|Out-File)\s*[\"']?([\w./\\-]+\.[A-Za-z0-9]+)")
SQL_PATHS = re.compile(r"FROM\s+'([^']+\.(?:csv|parquet|json|xlsx))'", re.IGNORECASE)
MAKES_DIR = re.compile(r"(?:mkdir(?:\s+-p)?|makedirs|md)\s*\(?\s*[\"']?([\w./\\-]+)|Path\(\s*[\"']([^\"']+)[\"']\s*\)\.mkdir")
EXTENSIONS = frozenset(
    "csv xlsx xls parquet json jsonl txt png jpg jpeg svg gif db sqlite md py yaml yml toml html pdf zip ndjson".split()
)


def fileName(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").split("/")[-1]


def isDataFile(path: str) -> bool:
    if any(mark in path for mark in ("*", "{", "http", "://", "<", ">")):
        return False
    name = fileName(path)
    return "." in name and name.rsplit(".", 1)[-1].lower() in EXTENSIONS


def directoryOf(path: str) -> str | None:
    parts = path.replace("\\", "/").split("/")
    return parts[0] if len(parts) > 1 and parts[0] not in ("", ".", "..") else None


def mentionedBefore(doc: DocumentPrint, name: str, line: int) -> bool:
    """코드보다 앞선 산문이 그 이름을 부르면 출처를 설명한 것이다."""
    return any(s.line < line and name in s.text for s in doc.sentences)


@rule("inputFileSource", mechanism="contrast")
def inputFileSource(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """코드가 읽는 파일과 쓰는 폴더가 글 어디에서도 만들어지지 않은 자리.

    왜: 위에서 아래로 따라 하는 독자는 그 줄에서 파일 없음 오류로 멈춘다. 글쓴이 컴퓨터에는 있어서 글쓴이는 모른다.
    어디서: 실측. 블로그 004 에서 read_excel("sales_small.xlsx") 의 파일을 만드는 코드가 없었고 data 폴더가 어디에서도
        만들어지지 않았다. 사람 평가자가 두 라운드에 걸쳐 집었다. 읽기와 쓰기 함수 목록은 이 파일 위의 정규식이다.
    고치기: 파일을 만드는 코드 블록을 앞에 두거나, 산문에서 그 파일을 어떻게 준비하는지 이름을 불러 말한다.
    안 잡는 것: 앞선 코드가 쓴 파일. 앞선 산문이 이름을 부른 파일 (독자가 준비하는 것으로 본다). 별표와 URL 과
        서식 자리표시자가 든 경로. 폴더는 error 가 아니라 notice 다.
    """
    created: set[str] = set()
    for block in codeBlocksOf(doc):
        blockWrites: set[str] = set()
        blockDirs: set[str] = set()
        for _, code in block.lines:
            for match in WRITES.finditer(code):
                blockWrites.add(fileName(match.group(1)))
            for match in SHELL_WRITES.finditer(code):
                blockWrites.add(fileName(match.group(1)))
            for match in OPENS.finditer(code):
                mode = match.group(2) or "r"
                if any(flag in mode for flag in "wax"):
                    blockWrites.add(fileName(match.group(1)))
            for match in MAKES_DIR.finditer(code):
                blockDirs.add((match.group(1) or match.group(2)).replace("\\", "/").split("/")[0])
        created |= blockDirs
        for line, code in block.lines:
            reads = [m.group(1) for m in READS.finditer(code)]
            reads += [m.group(1) for m in OPENS.finditer(code) if not any(flag in (m.group(2) or "r") for flag in "wax")]
            reads += [m.group(1) for m in SQL_PATHS.finditer(code)]
            for path in reads:
                if not isDataFile(path):
                    continue
                name = fileName(path)
                if name in created or name in blockWrites or mentionedBefore(doc, name, block.startLine):
                    continue
                yield Finding(
                    "inputFileSource",
                    line,
                    code.strip(),
                    f"`{name}` 을 읽는데 글 어디에서도 만들지 않았다. 독자는 여기서 파일 없음 오류로 멈춘다",
                    None,
                    "error",
                    DOCUMENT,
                    block.index,
                )
            for path in [m.group(1) for m in WRITES.finditer(code)] + reads:
                if any(mark in path for mark in ("http", "://", "{", "<", ">", "*", "?")):
                    continue
                directory = directoryOf(path)
                if not directory or directory in created or mentionedBefore(doc, directory, block.startLine):
                    continue
                created.add(directory)
                yield Finding(
                    "inputFileSource",
                    line,
                    code.strip(),
                    f"`{directory}` 폴더를 쓰는데 글 어디에서도 만들지 않았다. 없으면 파일을 쓰다 멈춘다",
                    None,
                    NOTICE,
                    DOCUMENT,
                    block.index,
                )
        created |= blockWrites
