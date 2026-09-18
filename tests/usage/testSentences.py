"""문장 역인덱스. 토큰, 문장 고르기, varint, 만들기와 조회의 결정성."""

from __future__ import annotations

from pathlib import Path

import pytest

from hanlint.usage import buildIndex, indexTokens, loadIndex, readDocuments
from hanlint.usage.sentences import FILES, decodeVarints, encodeVarint, paragraphsOf, sentenceKey, sentencesOf

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "usage" / "corpus"
SHARED = "회사는 리스부채를 리스개시일에 지급되지 않은 리스료의 현재가치로 측정합니다."


def testTokensStripJosaAndAddBigrams():
    assert indexTokens("회사는 리스부채를 K-IFRS 기준으로 12% 측정합니다.") == [
        "회사", "리스부채", "리스", "스부", "부채", "k", "ifrs", "기준", "12", "측정합니다", "측정", "정합", "합니", "니다",
    ]  # fmt: skip
    assert indexTokens("이 는 입니다") == []


def testSentenceKeyFoldsSpacingAndNumbers():
    assert sentenceKey("전기  대비 12% 증가하였습니다.") == sentenceKey("전기 대비 8% 증가하였습니다.")
    assert sentenceKey("전기 대비 증가하였습니다.") != sentenceKey("전기 대비 감소하였습니다.")


def testParagraphsSkipHeadingsTablesFencesAndBullets():
    text = "# 제목\n\n| 구분 | 값 |\n|---|---|\n\n```\n코드입니다.\n```\n\n- 항목입니다.\n(가) 가나다.\n3. 셋째입니다.\n"
    assert list(paragraphsOf(text + "나.붙은 항목입니다.\n")) == ["항목입니다.", "가나다.", "셋째입니다.", "붙은 항목입니다."]
    assert list(sentencesOf("제목만 있는 줄\n마침표로 끝난다. 물음표로 끝나나? 3.5 초다.\n")) == [
        "마침표로 끝난다.",
        "물음표로 끝나나?",
        "3.5 초다.",
    ]


def testVarintRoundTrip():
    values = [0, 1, 127, 128, 300, 65535, 2**32 + 5]
    assert decodeVarints(b"".join(encodeVarint(value) for value in values)) == values


def testBuildIsDeterministicAndFoldsSharedSentences(tmp_path: Path):
    first = buildIndex("report", readDocuments(CORPUS), tmp_path / "one")
    second = buildIndex("report", readDocuments(CORPUS), tmp_path / "two")
    assert first == second and (first.documents, first.sentences, first.terms) == (3, 11, 135)
    for name in FILES:
        assert (tmp_path / "one" / "report" / name).read_bytes() == (tmp_path / "two" / "report" / name).read_bytes()
    lines = (tmp_path / "one" / "report" / "sentences.tsv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == f"3\ta001\t{SHARED}"
    assert not any("리스부채의 최초 측정금액" in line for line in lines), "제목은 문장이 아니다"
    assert not any("영업이익 = 매출" in line for line in lines), "코드 펜스 안은 문장이 아니다"


def testSearchRanksAndDescribes(tmp_path: Path):
    buildIndex("report", readDocuments(CORPUS), tmp_path)
    index = loadIndex("report", tmp_path)
    assert index is not None and index.documents == 3 and index.sentences == 11
    hits = index.search("리스부채 측정", 2)
    assert [hit.text for hit in hits] == [SHARED, "리스부채는 이자비용을 반영하여 증가하고 지급한 리스료를 반영하여 감소합니다."]
    assert hits[0].documents == 3 and hits[0].source == "a001" and hits[0].score > hits[1].score > 0
    assert [hit.text for hit in index.search("영업이익 감소 원인", 1)] == ["영업이익 감소의 주요 원인은 원재료 가격 상승입니다."]
    assert index.search("없는낱말", 5) == []
    assert index.search("리스부채", 0) == []
    assert index.search("리스부채 측정", 5) == index.search("측정 리스부채", 5), "질의 낱말의 차례는 결과를 바꾸지 않는다"


def testMissingOrForeignIndex(tmp_path: Path):
    assert loadIndex("report", tmp_path) is None
    buildIndex("report", readDocuments(CORPUS), tmp_path)
    (tmp_path / "report" / "meta.json").write_text('{"format": 99}', encoding="utf-8")
    with pytest.raises(ValueError, match="format"):
        loadIndex("report", tmp_path)
