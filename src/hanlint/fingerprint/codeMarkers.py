"""코드 줄에서 파일의 공급과 수요를 읽는다. 어떤 줄이 파일을 만들고 (쓰기, 폴더 만들기) 어떤 줄이 파일을 읽는가.

읽기와 쓰기 함수의 목록은 이 파일의 정규식이 정본이다. 독자 상태가 공급 (`createdIn`) 을 블록 순서로 쌓고
inputFileSource 가 수요 (`readsIn`) 를 그 상태에 대 본다. 줄마다 대조하므로 여러 줄에 걸친 호출은 보지 않는다.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

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
WRITE_MODES = "wax"
"""open 의 모드에 이 글자가 있으면 쓰기다. 없으면 (기본 r) 읽기다."""


def fileName(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").split("/")[-1]


def isWriteMode(mode: str | None) -> bool:
    return any(flag in (mode or "r") for flag in WRITE_MODES)


def createdIn(lines: Iterable[str]) -> tuple[frozenset[str], frozenset[str]]:
    """코드 줄들이 만드는 (파일 이름, 폴더 이름). 쓰기 함수, 셸 리다이렉션, 쓰기 모드의 open, mkdir 을 본다."""
    files: set[str] = set()
    dirs: set[str] = set()
    for code in lines:
        files.update(fileName(match.group(1)) for match in WRITES.finditer(code))
        files.update(fileName(match.group(1)) for match in SHELL_WRITES.finditer(code))
        files.update(fileName(match.group(1)) for match in OPENS.finditer(code) if isWriteMode(match.group(2)))
        dirs.update((match.group(1) or match.group(2)).replace("\\", "/").split("/")[0] for match in MAKES_DIR.finditer(code))
    return frozenset(files), frozenset(dirs)


def readsIn(code: str) -> list[str]:
    """한 줄이 읽는 경로. 읽기 함수, 읽기 모드의 open, SQL 의 FROM 차례다."""
    reads = [match.group(1) for match in READS.finditer(code)]
    reads += [match.group(1) for match in OPENS.finditer(code) if not isWriteMode(match.group(2))]
    reads += [match.group(1) for match in SQL_PATHS.finditer(code)]
    return reads


def writeTargets(code: str) -> list[str]:
    """한 줄이 쓰기 함수로 쓰는 경로 그대로. 그 경로의 폴더가 있는지 볼 때 쓴다."""
    return [match.group(1) for match in WRITES.finditer(code)]
