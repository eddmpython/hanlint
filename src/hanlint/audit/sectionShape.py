"""절마다 문단 수, 문장 수, 코드와 이미지와 표와 목록의 수."""

from __future__ import annotations

from ..document.model import CODE, IMAGE, LIST, TABLE
from ..fingerprint import DocumentPrint
from .shape import SectionShape


def sectionShapesOf(doc: DocumentPrint) -> tuple[SectionShape, ...]:
    shapes = []
    for section in doc.sections:
        if section.isIntro and not section.blockKinds:
            continue
        shapes.append(
            SectionShape(
                index=section.index,
                title=section.title or "(도입)",
                level=section.level,
                startLine=section.startLine,
                paragraphs=len(section.paragraphs),
                sentences=sum(p.sentenceCount for p in section.paragraphs),
                codeBlocks=section.count(CODE),
                images=section.count(IMAGE),
                tables=section.count(TABLE),
                lists=section.count(LIST),
                hasProse=section.hasProse,
            )
        )
    return tuple(shapes)
