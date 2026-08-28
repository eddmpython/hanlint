from hanlint.document import parseMarkdown, plainText

SAMPLE = """---
title: 제목입니다
primaryKeyword: 파이썬 린터
---

도입 첫 문단입니다.

![그림](https://example.com/a.webp "캡션")

## 첫 절

첫 절의 문단입니다.
둘째 줄까지 이어집니다.

```python
# 이것은 코드 안의 주석이라 제목이 아니다
print("핵심은 속도입니다")
```

- 목록 하나
- 목록 둘

| 열 | 값 |
|---|---|
| a | 1 |

https://example.com/embed

### 소제목

## 둘째 절
둘째 절 문단.
"""


def testFrontmatterAndFirstLine():
    doc = parseMarkdown(SAMPLE)
    assert doc.frontmatter == {"title": "제목입니다", "primaryKeyword": "파이썬 린터"}
    assert doc.blocks[0].text == "도입 첫 문단입니다."
    assert doc.blocks[0].startLine == 6


def testBlockKinds():
    kinds = [b.kind for b in parseMarkdown(SAMPLE).blocks]
    assert kinds == [
        "prose",
        "image",
        "heading",
        "prose",
        "code",
        "list",
        "table",
        "embed",
        "heading",
        "heading",
        "prose",
    ]


def testCodeFenceDoesNotLeak():
    doc = parseMarkdown(SAMPLE)
    assert [h.text for h in doc.headings()] == ["첫 절", "소제목", "둘째 절"]
    assert all("핵심은" not in b.text for b in doc.prose())


def testSectionsSplitOnH2Only():
    doc = parseMarkdown(SAMPLE)
    assert [s.title for s in doc.sections] == ["", "첫 절", "둘째 절"]
    assert [b.kind for b in doc.sections[1].blocks] == ["prose", "code", "list", "table", "embed", "heading"]
    assert doc.sections[1].blocks[-1].level == 3


def testLineNumbersFollowSource():
    doc = parseMarkdown(SAMPLE)
    code = next(b for b in doc.blocks if b.kind == "code")
    assert (code.startLine, code.endLine) == (15, 18)
    assert doc.blocks[-1].text == "둘째 절 문단."
    assert doc.blocks[-1].startLine == 32
    assert [b.index for b in doc.blocks] == list(range(len(doc.blocks)))


def testHeadingGluedToParagraphIsOwnBlock():
    assert [b.kind for b in parseMarkdown("## 절\n바로 붙은 문단.\n").blocks] == ["heading", "prose"]


def testNoFrontmatter():
    doc = parseMarkdown("그냥 본문.\n")
    assert doc.frontmatter == {}
    assert doc.blocks[0].startLine == 1
    assert doc.bodySections == []
    assert doc.intro.prose()[0].text == "그냥 본문."


def testUnclosedFenceIsCode():
    doc = parseMarkdown("설명.\n\n```python\nprint(1)\n")
    assert [b.kind for b in doc.blocks] == ["prose", "code"]


def testInlineTripleBackticksDoNotOpenFence():
    text = "```kubectl -A```\n\n```bash\n# 셸 주석이다\nkubectl get pods\n```\n"
    doc = parseMarkdown(text)
    assert doc.headings() == []
    assert [block.kind for block in doc.blocks] == ["prose", "code"]


def testIndentedCodeAndQuoteAreNotProse():
    text = "설명.\n\n    root 1 ...\n    root 2 ...\n\n> 인용은 ... 그대로 둔다.\n"
    doc = parseMarkdown(text)
    assert [block.kind for block in doc.blocks] == ["prose", "code", "quote"]
    assert [block.text for block in doc.prose()] == ["설명."]


def testIndentedListParagraphIsProseButDeeperCodeIsCode():
    text = "1. 단계입니다.\n\n    목록 안 설명입니다.\n\n        result: ok\n\n목록 밖입니다.\n"
    doc = parseMarkdown(text)
    assert [block.kind for block in doc.blocks] == ["list", "prose", "code", "prose"]
    assert [block.text for block in doc.prose()] == ["    목록 안 설명입니다.", "목록 밖입니다."]


def testPlainTextStripsMarkup():
    assert plainText("`read_csv` 를 [문서](https://x)에서 **강조**해 *봅니다*") == "read_csv 를 문서에서 강조해 봅니다"
    assert plainText("줄 하나\n줄 둘") == "줄 하나\n줄 둘"
