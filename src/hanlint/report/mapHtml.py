"""지문 지도의 HTML 꼴. 단일 파일, 인라인 CSS, 의존성 0.

위에는 절마다 문장 셀이 색으로 칠해진 지도, 아래에는 같은 색이 배경으로 깔린 원문. 셀에 마우스를 올리면
지적이 뜨고 클릭하면 원문의 그 문장으로 간다.
"""

from __future__ import annotations

from html import escape

from ..fingerprint import DocumentPrint
from ..rules import Finding
from .holeKinds import allKinds, kindOf
from .mapText import groupFindings, worst

STYLE = """
body { font-family: system-ui, sans-serif; background: #fafafa; color: #222; margin: 0; padding: 24px; }
h1 { font-size: 18px; margin: 0 0 8px; }
.meta { color: #666; font-size: 13px; margin-bottom: 16px; }
.legend span { display: inline-block; margin-right: 12px; font-size: 12px; }
.legend i { display: inline-block; width: 12px; height: 12px; border-radius: 2px; vertical-align: middle; margin-right: 4px; }
.section { margin: 10px 0; }
.title { display: inline-block; width: 220px; font-size: 13px; color: #444; vertical-align: top; }
.cells { display: inline-block; }
.para { display: inline-block; margin-right: 8px; padding-bottom: 3px; border-bottom: 3px solid transparent; }
.cell { display: inline-block; width: 10px; height: 16px; background: #d8d8d8; margin-right: 1px; border-radius: 2px; }
.cell.hole { color: #fff; font-size: 10px; text-align: center; line-height: 16px; width: 14px; }
.badge { display: inline-block; padding: 1px 6px; border-radius: 3px; color: #fff; font-size: 12px; margin-right: 6px; }
.text { margin-top: 28px; max-width: 860px; line-height: 1.7; font-size: 15px; }
.text h2 { font-size: 16px; margin: 20px 0 6px; }
.text .s { padding: 1px 2px; border-radius: 2px; }
.text .s.hole { color: #111; }
.note { color: #666; font-size: 12px; margin-top: 24px; }
"""


def cellStyle(finding: Finding | None) -> tuple[str, str, str]:
    if not finding:
        return "cell", "", ""
    kind = kindOf(finding.rule)
    title = f"[{finding.rule}] {finding.why}" + (f"  고친 뒤: {finding.fix}" if finding.fix else "")
    return "cell hole", f"background:{kind.hex}", escape(title, quote=True)


def renderMapHtml(doc: DocumentPrint, findings: list[Finding]) -> str:
    grouped = groupFindings(findings)
    name = escape(doc.path or "글")
    parts = [f'<!doctype html><meta charset="utf-8"><title>{name} 지문 지도</title><style>{STYLE}</style>']
    parts.append(f"<h1>{name}</h1>")
    parts.append(
        f'<div class="meta">문장 {len(doc.sentences)} · 문단 {len(doc.paragraphs)} · 절 {len(doc.bodySections)}'
        f" · 지적 {len(findings)}</div>"
    )
    legend = "".join(f'<span><i style="background:{k.hex}"></i>{k.symbol} {escape(k.name)}</span>' for k in allKinds())
    parts.append(f'<div class="legend">{legend}</div>')
    documentFindings = [worst(grouped.get(("document", at), [])) for at in {f.at for f in findings if f.scope == "document"}]
    badges = "".join(
        f'<span class="badge" style="background:{kindOf(f.rule).hex}" title="{escape(f.why, quote=True)}">'
        f"{kindOf(f.rule).symbol} {f.rule} ({f.line}행)</span>"
        for f in documentFindings
        if f is not None
    )
    if badges:
        parts.append(f'<div class="meta">{badges}</div>')

    for section in doc.sections:
        if section.isIntro and not section.paragraphs:
            continue
        title = "도입" if section.isIntro else section.title
        sectionFinding = worst(grouped.get(("section", section.index), []))
        badge = ""
        if sectionFinding:
            kind = kindOf(sectionFinding.rule)
            badge = f'<span class="badge" style="background:{kind.hex}">{kind.symbol}</span>'
        cells = []
        for paragraph in section.paragraphs:
            paragraphFinding = worst(grouped.get(("paragraph", paragraph.index), []))
            border = f"border-bottom-color:{kindOf(paragraphFinding.rule).hex}" if paragraphFinding else ""
            hint = escape(f"[{paragraphFinding.rule}] {paragraphFinding.why}", quote=True) if paragraphFinding else ""
            inner = []
            for sentence in paragraph.sentences:
                cls, style, hint2 = cellStyle(worst(grouped.get(("sentence", sentence.index), [])))
                symbol = kindOf(worst(grouped[("sentence", sentence.index)]).rule).symbol if cls == "cell hole" else ""
                inner.append(f'<a class="{cls}" style="{style}" title="{hint2}" href="#s{sentence.index}">{symbol}</a>')
            cells.append(f'<span class="para" style="{border}" title="{hint}">{"".join(inner)}</span>')
        parts.append(
            f'<div class="section"><span class="title">{badge}{section.index} {escape(title)}</span>'
            f'<span class="cells">{"".join(cells)}</span></div>'
        )

    parts.append('<div class="text">')
    for section in doc.sections:
        if not section.isIntro:
            parts.append(f"<h2>{escape(section.title)}</h2>")
        for paragraph in section.paragraphs:
            spans = []
            for sentence in paragraph.sentences:
                finding = worst(grouped.get(("sentence", sentence.index), []))
                if finding:
                    kind = kindOf(finding.rule)
                    spans.append(
                        f'<span id="s{sentence.index}" class="s hole" style="background:{kind.hex}55"'
                        f' title="{escape(finding.why, quote=True)}">{escape(sentence.text)}</span>'
                    )
                else:
                    spans.append(f'<span id="s{sentence.index}" class="s">{escape(sentence.text)}</span>')
            parts.append("<p>" + " ".join(spans) + "</p>")
    parts.append("</div>")
    parts.append('<div class="note">숫자와 자리와 색만 있다. 점수도 등급도 없다. hanlint</div>')
    return "\n".join(parts)
