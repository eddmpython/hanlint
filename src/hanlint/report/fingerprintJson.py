"""지문 계층의 JSON 꼴. 층마다 한 번씩만 적고 위층은 아래층을 index 로 가리킨다.

dataclasses.asdict 는 절 안에 문단, 문단 안에 문장을 다시 적어 세 배로 부풀었다. 여기서는 문장, 문단, 절, 글의
네 목록을 따로 두고 `--layer` 로 하나만 고를 수 있다. 실수는 소수 여섯째 자리로 맞추고 정수면 정수로 적어
npm 구현과 글자 단위로 같게 한다.
"""

from __future__ import annotations

import json

from ..fingerprint import DocumentPrint, ParagraphPrint, SectionPrint, SentencePrint

LAYERS = ("all", "sentences", "paragraphs", "sections", "document")


def num(value: float | None) -> float | int | None:
    if value is None:
        return None
    rounded = round(value, 6)
    return int(rounded) if rounded == int(rounded) else rounded


def sentenceDict(s: SentencePrint) -> dict:
    return {
        "index": s.index,
        "line": s.line,
        "text": s.text,
        "blockIndex": s.blockIndex,
        "paragraphIndex": s.paragraphIndex,
        "sectionIndex": s.sectionIndex,
        "length": s.length,
        "ending": s.ending,
        "mood": s.mood,
        "register": s.register,
        "commas": s.commas,
        "connectorStart": s.connectorStart,
        "causal": s.causal,
        "deixis": list(s.deixis),
        "euiCount": s.euiCount,
        "nounRun": s.nounRun,
        "passives": list(s.passives),
        "hedges": s.hedges,
        "numbers": s.numbers,
        "topics": sorted(s.topics),
        "promises": list(s.promises),
        "recalls": list(s.recalls),
        "countPromises": [[n, unit, text] for n, unit, text in s.countPromises],
        "readerCall": s.readerCall,
        "matches": [
            {
                "dictionary": m.dictionary,
                "text": m.text,
                "start": m.start,
                "end": m.end,
                "why": m.why,
                "source": m.source,
                "fix": m.fix,
            }
            for m in s.matches
        ],
        "quoted": [[start, end] for start, end in s.quoted],
    }


def paragraphDict(p: ParagraphPrint) -> dict:
    return {
        "index": p.index,
        "blockIndex": p.blockIndex,
        "sectionIndex": p.sectionIndex,
        "startLine": p.startLine,
        "endLine": p.endLine,
        "sentences": [s.index for s in p.sentences],
        "sentenceCount": p.sentenceCount,
        "meanLength": num(p.meanLength),
        "lengthStd": num(p.lengthStd),
        "causalTotal": p.causalTotal,
        "deixisTotal": p.deixisTotal,
        "topics": sorted(p.topics),
        "overlapWithPrevious": num(p.overlapWithPrevious),
        "followsProseDirectly": p.followsProseDirectly,
    }


def sectionDict(s: SectionPrint) -> dict:
    return {
        "index": s.index,
        "title": s.title,
        "level": s.level,
        "startLine": s.startLine,
        "paragraphs": [p.index for p in s.paragraphs],
        "blockKinds": list(s.blockKinds),
        "topics": sorted(s.topics),
        "isIntro": s.isIntro,
    }


def documentDict(doc: DocumentPrint) -> dict:
    return {
        "path": doc.path,
        "frontmatter": dict(doc.frontmatter),
        "headings": [[level, text, line] for level, text, line in doc.headings],
        "wordCount": doc.wordCount,
        "sentenceCount": len(doc.sentences),
        "paragraphCount": len(doc.paragraphs),
        "sectionCount": len(doc.sections),
        "questionCount": doc.questionCount,
        "readerCallCount": doc.readerCallCount,
        "register": doc.register,
        "registerShare": num(round(doc.registerShare, 3)),
        "countPromises": [[n, unit, line, text] for n, unit, line, text in doc.countPromises],
        "promises": [[line, text] for line, text in doc.reader.final.promises],
        "recalls": [[line, text] for line, text in doc.reader.final.recalls],
        "disabled": [[name, start, end] for name, start, end in doc.disabled],
    }


def fingerprintDict(doc: DocumentPrint, layer: str = "all") -> dict:
    data: dict = {"version": 1, "layer": layer}
    if layer in ("all", "document"):
        data["document"] = documentDict(doc)
    if layer in ("all", "sections"):
        data["sections"] = [sectionDict(s) for s in doc.sections]
    if layer in ("all", "paragraphs"):
        data["paragraphs"] = [paragraphDict(p) for p in doc.paragraphs]
    if layer in ("all", "sentences"):
        data["sentences"] = [sentenceDict(s) for s in doc.sentences]
    return data


def renderFingerprintJson(doc: DocumentPrint, layer: str = "all") -> str:
    return json.dumps(fingerprintDict(doc, layer), ensure_ascii=False, indent=2)
