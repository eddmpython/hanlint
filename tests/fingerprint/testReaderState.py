"""독자 상태가 블록과 문장 순서대로 쌓이는지. 한 자리의 상태는 그 자리보다 앞의 것만 든다."""

from __future__ import annotations

from hanlint import fingerprint

TEXT = '표를 만듭니다. 값은 12개입니다.\n\n```python\ndf.to_csv("out/result.csv")\n```\n\n결과가 30줄입니다. 이것을 봅니다.\n'


def testStatesFollowReadingOrder():
    doc = fingerprint(TEXT)
    trail = doc.reader
    assert len(trail.beforeSentence) == len(doc.sentences) == 4
    assert len(trail.beforeBlock) == len(doc.blocks)
    first = trail.beforeSentence[0]
    assert first.previous is None and first.recent == frozenset() and first.numerals == frozenset()
    second = trail.beforeSentence[1]
    assert second.previous is doc.sentences[0] and "표" in second.recent
    # 코드 블록을 지난 자리. 앞 산문의 수와 코드가 만든 파일을 들고 있고 아직 자기 수는 모른다.
    third = trail.beforeSentence[2]
    assert third.numerals == frozenset({"12"})
    assert third.files == frozenset({"result.csv"})
    assert third.sentencesRead == 2 and third.previous is doc.sentences[1]
    assert trail.final.sentencesRead == 4 and trail.final.numerals == frozenset({"12", "30"})
    assert trail.final.promises == () and trail.final.recalls == ()


def testBlockStateIsTheStateBeforeThatBlock():
    doc = fingerprint(TEXT)
    code = doc.codeBlocks[0]
    before = doc.reader.beforeBlock[code.index]
    assert before.files == frozenset() and before.numerals == frozenset({"12"}) and before.sentencesRead == 2


def testMentionedBeforeLooksOnlyAtEarlierProse():
    doc = fingerprint('sales.csv 를 준비합니다.\n\n```python\npd.read_csv("sales.csv")\n```\n\n뒤에서 data.csv 를 만듭니다.\n')
    code = doc.codeBlocks[0]
    assert doc.reader.mentionedBefore(code.index, "sales.csv")
    assert not doc.reader.mentionedBefore(code.index, "data.csv")


def testPromisesAndRecallsAccumulateInOrder():
    doc = fingerprint("자세한 것은 뒤에서 다루겠습니다.\n\n앞에서 미룬 것을 여기서 봅니다.\n")
    states = doc.reader.beforeSentence
    assert states[0].promises == () and states[1].promises == ((1, "뒤에서 다루"),)
    assert states[1].recalls == () and doc.reader.final.recalls == ((3, "앞에서 미룬"),)
