"""지문 지도의 터미널 꼴.

문장 하나가 셀 하나. 문단 경계는 공백, 절마다 줄을 바꾼다. 정상은 무채색 블록이고 구멍이 있는 셀은 구멍
종류의 기호와 색이다. 문단 구멍은 셀 묶음 아래 밑줄, 절과 글 구멍은 배지. 색은 ANSI 256 이고 기호로 이중
코딩하므로 색이 없어도 읽힌다.
"""

from __future__ import annotations

from collections import defaultdict

from ..fingerprint import DocumentPrint
from ..rules import Finding
from .holeKinds import HoleKind, kindOf

CELL = "▇"
UNDERLINE = "‾"
ESC = chr(27)
TITLE_WIDTH = 14


def paint(text: str, kind: HoleKind | None, color: bool) -> str:
    if not color or kind is None:
        return text
    return f"{ESC}[38;5;{kind.ansi}m{text}{ESC}[0m"


def worst(findings: list[Finding]) -> Finding | None:
    if not findings:
        return None
    return sorted(findings, key=lambda f: (f.severity != "error", f.rule))[0]


def groupFindings(findings: list[Finding]) -> dict[tuple[str, int], list[Finding]]:
    grouped: dict[tuple[str, int], list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[(finding.scope, finding.at)].append(finding)
    return grouped


def displayWidth(text: str) -> int:
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)


def fitTitle(title: str) -> str:
    out = ""
    for ch in title:
        if displayWidth(out + ch) > TITLE_WIDTH:
            break
        out += ch
    return out + " " * (TITLE_WIDTH - displayWidth(out))


def renderMap(doc: DocumentPrint, findings: list[Finding], color: bool = False) -> str:
    grouped = groupFindings(findings)
    lines: list[str] = []
    name = doc.path or "글"
    badges = [worst(grouped.get(("document", at), [])) for at in {f.at for f in findings if f.scope == "document"}]
    badgeText = "  ".join(
        f"{paint(kindOf(f.rule).symbol, kindOf(f.rule), color)} {f.rule} ({f.line}행)" for f in badges if f is not None
    )
    header = f"{name}  문장 {len(doc.sentences)}  문단 {len(doc.paragraphs)}  절 {len(doc.bodySections)}"
    lines.append(header + (f"        배지: {badgeText}" if badgeText else ""))
    lines.append("")
    legendAt = len(lines)
    shown: set = set()

    for section in doc.sections:
        if section.isIntro and not section.paragraphs:
            continue
        title = "도입" if section.isIntro else section.title
        sectionFinding = worst(grouped.get(("section", section.index), []))
        # 기호는 제 칸을 갖는다. 전에는 제목의 첫 글자를 덮어써서 `단계별` 이 `S계별` 이 됐다
        mark = " "
        if sectionFinding:
            kind = kindOf(sectionFinding.rule)
            mark = paint(kind.symbol, kind, color)
            shown.add(kind)
        prefix = f"{section.index:>2} {mark} {fitTitle(title)} "
        cells: list[str] = []
        columns: list[tuple[int, int]] = []
        cursor = displayWidth(prefix)
        for paragraph in section.paragraphs:
            start = cursor
            for sentence in paragraph.sentences:
                finding = worst(grouped.get(("sentence", sentence.index), []))
                if finding:
                    kind = kindOf(finding.rule)
                    cells.append(paint(kind.symbol, kind, color))
                else:
                    cells.append(CELL)
                cursor += 1
            columns.append((start, cursor))
            cells.append(" ")
            cursor += 1
        lines.append(prefix + "".join(cells).rstrip())
        for paragraph, (start, end) in zip(section.paragraphs, columns, strict=True):
            finding = worst(grouped.get(("paragraph", paragraph.index), []))
            if not finding:
                continue
            kind = kindOf(finding.rule)
            marker = paint(UNDERLINE * (end - start), kind, color)
            label = f" {paint(kind.symbol, kind, color)} {kind.name} {finding.rule} ({finding.line}행)"
            lines.append(" " * start + marker + label)
    # 기호만 나온 자리 (문장 칸과 절 배지) 를 위한 범례. 이름 없는 글자를 지도에 두지 않는다
    if shown:
        legend = "  ".join(f"{paint(kind.symbol, kind, color)} {kind.name}" for kind in sorted(shown, key=lambda k: k.symbol))
        lines.insert(legendAt, f"기호: {legend}")
        lines.insert(legendAt + 1, "")
    return "\n".join(lines)
