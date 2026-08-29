from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.codeMarkers import createdIn, fileName, readsIn, writeTargets
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule

EXTENSIONS = frozenset(
    "csv xlsx xls parquet json jsonl txt png jpg jpeg svg gif db sqlite md py yaml yml toml html pdf zip ndjson".split()
)
NOT_A_FILE = ("*", "{", "http", "://", "<", ">")
"""별표, 서식 자리표시자, URL 이 든 경로는 파일 하나를 가리키지 않는다."""
NOT_A_PATH = NOT_A_FILE + ("?",)
"""폴더를 볼 때는 물음표까지 뺀다."""


def isDataFile(path: str) -> bool:
    if any(mark in path for mark in NOT_A_FILE):
        return False
    name = fileName(path)
    return "." in name and name.rsplit(".", 1)[-1].lower() in EXTENSIONS


def directoryOf(path: str) -> str | None:
    parts = path.replace("\\", "/").split("/")
    return parts[0] if len(parts) > 1 and parts[0] not in ("", ".", "..") else None


@rule("inputFileSource", mechanism="reader")
def inputFileSource(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """코드가 읽는 파일과 쓰는 폴더가 글 어디에서도 만들어지지 않은 자리.

    왜: 위에서 아래로 따라 하는 독자는 그 줄에서 파일 없음 오류로 멈춘다. 글쓴이 컴퓨터에는 있어서 글쓴이는 모른다.
    어디서: 실측. 블로그 004 에서 read_excel("sales_small.xlsx") 의 파일을 만드는 코드가 없었고 data 폴더가 어디에서도
        만들어지지 않았다. 사람 평가자가 두 라운드에 걸쳐 집었다. 읽기와 쓰기 함수 목록은 fingerprint/codeMarkers.py 의
        정규식이고, 앞선 코드가 만든 파일은 독자 상태 (fingerprint/readerState.py) 의 files 다.
    고치기: 파일을 만드는 코드 블록을 앞에 두거나, 산문에서 그 파일을 어떻게 준비하는지 이름을 불러 말한다.
    안 잡는 것: 앞선 코드가 쓴 파일. 앞선 산문이 이름을 부른 파일 (독자가 준비하는 것으로 본다). 별표와 URL 과
        서식 자리표시자가 든 경로. 폴더는 error 가 아니라 notice 다.
    """
    reported: set[str] = set()  # 이미 짚은 폴더. 같은 폴더를 두 번 짚지 않는다
    for block in doc.codeBlocks:
        reader = doc.reader.beforeBlock[block.index]
        blockWrites, blockDirs = createdIn(line for _, line in block.lines)
        # 이 블록이 만드는 폴더는 같은 블록의 읽기에도 미리 센다. 파일은 블록 안에서 쓴 것 (blockWrites) 만 따로 본다.
        have = set(reader.files) | blockDirs | reported
        for line, code in block.lines:
            reads = readsIn(code)
            for path in reads:
                if not isDataFile(path):
                    continue
                name = fileName(path)
                if name in have or name in blockWrites or doc.reader.mentionedBefore(block.index, name):
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
            for path in writeTargets(code) + reads:
                if any(mark in path for mark in NOT_A_PATH):
                    continue
                directory = directoryOf(path)
                if not directory or directory in have or doc.reader.mentionedBefore(block.index, directory):
                    continue
                have.add(directory)
                reported.add(directory)
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
