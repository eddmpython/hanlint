"""글 시트. 소스에서 뽑은 글 마디와 지적을 마크다운 표 하나로 내고, 사람이 고친 표를 다시 읽는다.

지적은 파일마다 흩어져 나오고 사람은 한 번에 보고 싶어 한다. 표 하나에 모든 글이 있으면 어느 화면의 어느 말이
남았는지 한눈에 보이고, `고침` 칸에 새 글을 적으면 `hanlint sheet apply` 가 그 자리를 파일에 되돌려 쓴다.
표의 정본은 이 모듈이 낸 마크다운이고 사람은 `고침` 칸만 채운다. 나머지 칸을 고치면 자리를 못 찾는다.

칸: 번호, 자리 (`경로:줄:칸`. 칸은 그 줄에서 글이 시작하는 자리라 같은 글이 두 번 있어도 되돌려 쓸 곳이 하나다), 글,
지적 (규칙: 이유. 여럿이면 ` / ` 로 잇는다), 고침 (비워 둔다).
`|` 는 `\\|` 로, 줄바꿈은 없다 (한 줄 글만 뽑는다).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from ..config import Config
from ..document import parseMarkdown, sourceLiterals
from ..fingerprint import buildFingerprint
from ..rules import Finding, runAll

HEADER = ("번호", "자리", "글", "지적", "고침")
ROW_PATTERN = re.compile(r"^\|(.*)\|$")


@dataclass(frozen=True)
class SheetRow:
    file: str
    """작업 폴더 기준 상대 경로. 구분자는 언제나 `/` 다."""
    line: int
    text: str
    findings: tuple[Finding, ...] = ()
    fix: str = ""
    """사람이 표에 적은 고친 글. 뽑을 때는 비어 있다."""
    column: int = 0
    """1부터 세는 칸. 0 이면 모른다 (사람이 손으로 적은 줄). 알면 되돌려 쓸 자리가 하나로 정해진다."""

    @property
    def place(self) -> str:
        return f"{self.file}:{self.line}:{self.column}" if self.column > 0 else f"{self.file}:{self.line}"


def prefilledFix(literal, findings: tuple[Finding, ...]) -> str:
    """지적이 하나이고 그 지적에 고침이 있으면 고침 칸에 미리 적는다.

    고침은 문장 단위라 글이 문장 하나 그대로일 때 (식이 없고 문장 부호로 나뉘지 않을 때) 만 글 전체와 같다.
    """
    if literal.plain != literal.text or len(findings) != 1:
        return ""
    only = findings[0]
    return only.fix if only.fix is not None and only.quote == literal.plain else ""


def sheetRows(sources: Iterable[tuple[str, str]], config: Config, everything: bool = False) -> list[SheetRow]:
    """(이름표, 소스) 마다 글을 뽑아 규칙을 돌리고 표의 행을 만든다. 지적은 `error` 만 남긴다.

    이름표는 표의 `자리` 가 되는 경로다. 소스를 읽는 쪽 (CLI 는 디스크, 브라우저는 저장소) 이 다르므로
    읽기는 밖에 두고 여기서는 문자열만 받는다. 파이썬과 npm 이 같은 행을 내는지는 testSheetAgrees 가 본다.
    """
    rows: list[SheetRow] = []
    for label, source in sources:
        for literal in sourceLiterals(source, label):
            findings = tuple(
                finding
                for finding in runAll(buildFingerprint(parseMarkdown(literal.plain), config), config)
                if finding.severity == "error"
            )
            if findings or everything:
                fix = prefilledFix(literal, findings)
                rows.append(SheetRow(label, literal.line, literal.text, findings, fix, literal.column))
    return rows


def escapeCell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|")


def unescapeCell(text: str) -> str:
    return text.replace("\\|", "|").replace("\\\\", "\\")


def splitRow(line: str) -> list[str] | None:
    """`| a | b |` 를 칸으로. `\\|` 는 칸 경계가 아니다."""
    match = ROW_PATTERN.match(line.strip())
    if not match:
        return None
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in match.group(1):
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            current.append(char)
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    cells.append("".join(current).strip())
    return cells


def findingCell(findings: tuple[Finding, ...]) -> str:
    return " / ".join(f"{finding.rule}: {finding.why}" for finding in findings)


def renderSheet(rows: list[SheetRow], preset: str, fileCount: int) -> str:
    """사람이 읽고 고치는 마크다운 표."""
    flagged = sum(1 for row in rows if row.findings)
    lines = [
        "# hanlint sheet",
        "",
        f"프리셋 {preset}, 파일 {fileCount}개, 글 {len(rows)}개, 지적 있는 글 {flagged}개. "
        "고침 칸에 새 글을 적고 `hanlint sheet apply 이파일.md` 로 되돌려 쓴다. 다른 칸은 고치지 않는다.",
        "",
        "| " + " | ".join(HEADER) + " |",
        "| " + " | ".join("---" for _ in HEADER) + " |",
    ]
    for number, row in enumerate(rows, 1):
        cells = (str(number), row.place, row.text, findingCell(row.findings), row.fix)
        lines.append("| " + " | ".join(escapeCell(cell) for cell in cells) + " |")
    return "\n".join(lines)


def renderSheetJson(rows: list[SheetRow], preset: str, fileCount: int) -> str:
    """기계가 읽는 꼴. 에이전트가 표 대신 받는다."""
    data = {
        "version": 1,
        "preset": preset,
        "files": fileCount,
        "rows": [
            {
                "file": row.file,
                "line": row.line,
                "column": row.column,
                "text": row.text,
                "findings": [{"rule": finding.rule, "why": finding.why} for finding in row.findings],
                "fix": row.fix,
            }
            for row in rows
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


@dataclass
class ParsedSheet:
    rows: list[SheetRow] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    """읽지 못한 줄. 자리 꼴이 아니거나 칸 수가 다른 것."""


def parseSheet(markdown: str) -> ParsedSheet:
    """사람이 고친 표를 읽는다. 머리글과 구분선은 넘기고 `고침` 이 있는 줄만 남긴다."""
    parsed = ParsedSheet()
    for lineNumber, raw in enumerate(markdown.split("\n"), 1):
        cells = splitRow(raw)
        if cells is None:
            continue
        if cells[: len(HEADER)] == list(HEADER) or all(cell.strip("-") == "" for cell in cells):
            continue
        if len(cells) != len(HEADER):
            parsed.problems.append(f"{lineNumber}행: 칸이 {len(cells)}개다. {len(HEADER)}개여야 한다")
            continue
        place = unescapeCell(cells[1])
        file, line, column = splitPlace(place)
        if file is None:
            parsed.problems.append(f"{lineNumber}행: 자리 `{place}` 가 경로:줄 이나 경로:줄:칸 꼴이 아니다")
            continue
        fix = unescapeCell(cells[4])
        if not fix:
            continue
        parsed.rows.append(SheetRow(file, line, unescapeCell(cells[2]), (), fix, column))
    return parsed


def splitPlace(place: str) -> tuple[str | None, int, int]:
    """`경로:줄:칸` 이나 `경로:줄` 을 (경로, 줄, 칸) 으로. 칸이 없으면 0. 꼴이 아니면 경로가 None."""
    head, separator, last = place.rpartition(":")
    if not separator or not last.isdigit():
        return None, 0, 0
    front, separator2, middle = head.rpartition(":")
    if separator2 and middle.isdigit() and front:
        return front, int(middle), int(last)
    return head, int(last), 0


__all__ = ["HEADER", "ParsedSheet", "SheetRow", "parseSheet", "renderSheet", "renderSheetJson", "splitPlace", "splitRow"]
