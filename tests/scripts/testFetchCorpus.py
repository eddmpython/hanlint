from scripts.fetchCorpus import normalizeKubernetes, normalizeMdn, normalizeWikitext


def testWikitextListsAndHeadingsBecomeMarkdown():
    source = "== 제목 ==\n\n# 첫째\n## 둘째\n\n== 주석 및 라이선스 ==\n\nCC BY-SA"
    assert normalizeWikitext(source) == "## 제목\n\n1. 첫째\n  1. 둘째\n"


def testKubernetesMetadataIsNotPublishedProse():
    source = """---
title: 문서
---
{{% heading "prerequisites" %}}

{{< glossary_tooltip term_id="pod" text="파드" >}}를 만든다.

## 다음 {#next-step}
"""
    assert normalizeKubernetes(source) == "## 시작하기 전에\n\n파드를 만든다.\n\n## 다음\n"


def testMdnMacrosAndFrontmatterAreNotProse():
    source = """---
title: 문서
slug: Web/API/Thing
---
{{APIRef("DOM")}}

{{domxref("Element")}} 객체는 {{Compat}} 표 아래에 있다.

{{EmbedLiveSample("예제")}}
"""
    assert normalizeMdn(source) == "객체는  표 아래에 있다.\n"


def testWikitextFileLinksAndEmptyBulletsAreNotProse():
    source = "[[파일:A.jpg|섬네일|left|alt=설명|[[원각사]]의 사진]]\n본문이다.\n* {{cite web|url=x}}\n* 항목\n[[분류:역사]]\n"
    assert normalizeWikitext(source) == "본문이다.\n* 항목\n"


def testKubernetesMermaidBodyIsNotProse():
    source = "본문이다.\n\n{{< mermaid >}}\nflowchart LR\n  A --> B\n{{< /mermaid >}}\n\n끝이다.\n"
    assert normalizeKubernetes(source) == "본문이다.\n\n\n\n끝이다.\n"
