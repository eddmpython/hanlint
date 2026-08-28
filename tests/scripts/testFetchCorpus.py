from scripts.fetchCorpus import normalizeKubernetes, normalizeWikitext


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
