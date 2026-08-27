from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...document.model import TABLE
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule

SEPARATOR = re.compile(r"^:?-{2,}:?$")
MEASURE = re.compile(r"^([+-]?\d[\d,]*(?:\.\d+)?)\s*([^\s\d]{0,6})$")
EMPTY = ("", "-", "--")


def cellsOf(text: str) -> list[tuple[int, list[str]]]:
    """(블록 안 줄 오프셋, 칸 목록). 구분 줄은 뺀다."""
    rows: list[tuple[int, list[str]]] = []
    for offset, line in enumerate(text.split("\n")):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(SEPARATOR.match(cell) for cell in cells if cell):
            continue
        rows.append((offset, cells))
    return rows


def unitOf(cell: str) -> str | None:
    """`3.72초` 는 초, `533MB` 는 MB, `직접 부르지 않음` 은 None. 잰 값 하나인 칸만 단위를 준다."""
    match = MEASURE.match(cell)
    return match.group(2) if match else None


@rule("tableOddCell")
def tableOddCell(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """한 열이 전부 같은 단위로 잰 값인데 한 칸만 다른 것을 담은 표.

    왜: 독자는 표의 한 열을 같은 잣대로 훑는다. 그 가운데 한 칸만 다른 것을 재고 있으면 훑던 눈이 그 자리에서
        멈추고, 그 칸이 다른 뜻이라는 것을 본문에서 다시 찾아야 한다.
    어디서: 실측. 블로그 004 의 여섯 라이브러리 비교표에서 시간 열 아홉 칸 중 여덟 칸이 초인데 한 칸이
        `직접 부르지 않음` 이었고, 메모리 열도 여덟 칸이 MB 인데 한 칸이 `넘길 때 453MB 에서 700MB` 였다.
        평가자가 표를 훑다가 열의 뜻이 바뀌는 자리에서 멈춘다고 집었다. 임계는 config.tableOddCellMinRows.
    고치기: 그 칸을 같은 잣대로 다시 재거나, 그 줄을 표에서 빼서 본문 문장으로 옮긴다. 표에 남겨야 하면 열을
        나눠 다른 잣대라는 것을 열 제목으로 보인다.
    안 잡는 것: 줄이 tableOddCellMinRows 보다 적은 표. 첫 열 (이름 열이라 재는 값이 아니다). 빈 칸과 `-`.
        딴 칸이 둘 이상인 열 (그 열은 원래 자유 서술이다). 근사라 notice 로만 낸다.
    """
    for block in doc.blocks:
        if block.kind != TABLE:
            continue
        rows = cellsOf(block.text)
        if len(rows) < 2:
            continue
        body = rows[1:]
        width = min(len(cells) for _, cells in body)
        for column in range(1, width):
            values = [(offset, cells[column]) for offset, cells in body if cells[column] not in EMPTY]
            if len(values) < config.tableOddCellMinRows:
                continue
            units = [(offset, cell, unitOf(cell)) for offset, cell in values]
            odd = [(offset, cell) for offset, cell, unit in units if unit is None]
            kinds = {unit for _, _, unit in units if unit is not None}
            if len(odd) != 1 or len(kinds) != 1:
                continue
            unit = next(iter(kinds))
            offset, cell = odd[0]
            yield Finding(
                "tableOddCell",
                block.startLine + offset,
                cell,
                f"이 열의 나머지 {len(values) - 1}칸은 `{unit}` 으로 잰 값 하나인데 이 칸만 다르다. "
                "같은 잣대로 다시 재거나 그 줄을 본문 문장으로 옮긴다",
                None,
                NOTICE,
                DOCUMENT,
                block.index,
            )
