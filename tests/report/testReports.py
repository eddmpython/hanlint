import json

from hanlint import Config, auditText, fingerprint, lintText
from hanlint.report import (
    renderAudit,
    renderCompact,
    renderFingerprintJson,
    renderGithub,
    renderJson,
    renderMap,
    renderMapHtml,
    renderText,
)
from hanlint.report.holeKinds import kindOf

SAMPLE = """## 첫 절

핵심은 속도입니다. 모든 분야에 있어서 기준이 필요합니다.

첫 문장입니다.

둘째 문장입니다.

셋째 문장입니다.

## 둘째 절

값을 저장합니다. 저장한 값은 어디에 남을까요? 작업 폴더입니다.
"""


def testTextReportHasFileLineAndFix():
    findings = lintText(SAMPLE, path="글.md")
    text = renderText("글.md", findings)
    assert text.startswith("글.md  집은 자리")
    assert "글.md:3  [cliche]" in text
    assert "고친 뒤: 모든 분야에서 기준이 필요합니다." in text
    assert not text.endswith(chr(10))


def testTextReportWhenClean():
    assert renderText("글.md", []) == "글.md  집은 자리 없음"


def testJsonReportIsParseableAndCarriesFields():
    findings = lintText(SAMPLE, path="글.md")
    data = json.loads(renderJson({"글.md": findings}, {"글.md": auditText(SAMPLE)}))
    assert data["version"] == 1
    first = data["files"][0]["findings"][0]
    assert set(first) >= {"rule", "line", "severity", "scope", "at", "quote", "why"}
    assert data["files"][0]["audit"]["sentenceCount"] > 0


def testCompactReportIsOneLinePerFinding():
    findings = lintText(SAMPLE, path="글.md")
    lines = renderCompact("글.md", findings).splitlines()
    assert len(lines) == len(findings)
    assert any(line.startswith("글.md:3 [cliche] `핵심은`") for line in lines)
    assert any("고친 뒤: 모든 분야에서 기준이 필요합니다." in line for line in lines)
    assert renderCompact("글.md", []) == ""


def testJsonReportCarriesConfigAndFragments():
    findings = lintText(SAMPLE, path="글.md")
    data = json.loads(renderJson({"글.md": findings}, configLabel="hanlint.toml"))
    assert data["config"] == "hanlint.toml"
    translationese = next(f for f in data["files"][0]["findings"] if f["rule"] == "translationese")
    assert translationese["fragment"] == "에 있어서" and translationese["replacement"] == "에서"


def testFingerprintJsonLayers():
    doc = fingerprint(SAMPLE, path="글.md")
    data = json.loads(renderFingerprintJson(doc))
    assert set(data) == {"version", "layer", "document", "sections", "paragraphs", "sentences"}
    assert data["paragraphs"][0]["sentences"] == [0, 1]
    assert isinstance(data["paragraphs"][0]["meanLength"], (int, float))
    only = json.loads(renderFingerprintJson(doc, "sentences"))
    assert set(only) == {"version", "layer", "sentences"} and only["layer"] == "sentences"


def testGithubReportLines():
    findings = lintText(SAMPLE, path="글.md")
    lines = renderGithub("글.md", findings).splitlines()
    assert any(line.startswith("::error file=글.md,line=3::[cliche]") for line in lines)
    assert any(line.startswith("::notice") for line in lines) or all(f.severity == "error" for f in findings)


def testMapShowsSymbolsAndUnderlines():
    doc = fingerprint(SAMPLE, path="글.md")
    findings = lintText(SAMPLE, path="글.md")
    text = renderMap(doc, findings)
    assert "글.md  문장" in text
    assert kindOf("cliche").symbol in text
    assert "paraFragment" in text and "‾" in text
    colored = renderMap(doc, findings, color=True)
    assert chr(27) in colored


def testHoleKindsAreLoaded():
    from hanlint.report.holeKinds import allKinds, kindOf

    kinds = allKinds()
    assert len(kinds) >= 9
    assert kindOf("cliche").id == "wording" and kindOf("spelling").id == "orthography"
    assert kindOf("inputFileSource").id == "code"


def testMapHtmlIsSelfContained():
    doc = fingerprint(SAMPLE, path="글.md")
    findings = lintText(SAMPLE, path="글.md")
    html = renderMapHtml(doc, findings)
    assert html.startswith("<!doctype html>")
    assert html.count("<span><i") >= 9
    assert "<style>" in html and "http" not in html.split("<body")[0].replace("http-equiv", "")
    assert 'href="#s0"' in html and 'id="s0"' in html
    assert kindOf("cliche").hex in html


def testAuditReportHasNumbersAndNoScore():
    doc = fingerprint(SAMPLE, path="글.md")
    findings = lintText(SAMPLE, path="글.md", config=Config())
    audit = auditText(SAMPLE)
    text = renderAudit(doc, findings, audit, color=False)
    assert "문장 길이" in text and "종결어미" in text and "천 어절당" in text
    assert "어휘        어절" in text and "자주 쓴 말" in text
    assert audit.lexicon.tokens > audit.lexicon.types > 0 and 0 < audit.lexicon.typeTokenRatio <= 1
    assert "점수" not in text and "등급" not in text


def testAuditReportKeepsLongSectionTitlesWhole():
    title = "아주 긴 데이터프레임 라이브러리 제목을 끝까지 보여 준다"
    source = f"## {title}\n\n본문입니다.\n"
    text = renderAudit(fingerprint(source), lintText(source), auditText(source), color=False)
    assert title in text


def testJsonReportCarriesSafeOperationOutsideFindings():
    text = "첫 렌더 결과입니다."
    config = Config.fromMapping({"operations": [{"before": "렌더", "after": "렌더링", "presets": ["blog"]}]})
    doc = fingerprint(text, config, path="글.md")
    data = json.loads(
        renderJson(
            {"글.md": lintText(text, config, path="글.md")},
            preset=config.preset,
            documents={"글.md": doc},
            operations=config.operations,
        )
    )
    operation = data["files"][0]["operations"][0]["operation"]
    assert operation["result"] == "첫 렌더링 결과입니다."
