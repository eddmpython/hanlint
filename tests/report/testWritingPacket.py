import json

from hanlint import Config, writingPacket
from hanlint.report import renderWritingPacket

SAMPLE = """# 속도 보고

핵심은 처리 속도입니다. 설계에 대한 이해가 필요합니다.

## 결과

파일을 엽니다. 결과가 보일까요? 표에 3초라고 나옵니다.
"""


def testWritingPacketCarriesEvidenceWithoutDuplicatingExemplars():
    packet = writingPacket(SAMPLE, path="글.md")
    assert packet["kind"] == "hanlint.writingPacket" and packet["purpose"] == "revise"
    assert packet["input"]["text"] == SAMPLE and packet["input"]["preset"] == "blog"
    assert len(packet["input"]["textSha256"]) == 64
    assert packet["comparison"]["referenceProfile"]["source"] == "bundled:blog"
    assert packet["comparison"]["current"]["sentenceCount"] == 5
    assert packet["comparison"]["readerState"]["numbersSeen"] == ["3"]
    assert packet["findings"]["errorCount"] > 0
    names = [entry["rule"] for entry in packet["guidance"]]
    assert names == sorted(set(names)) and "cliche" in names and "translationese" in names
    assert all("exemplar" not in finding for finding in packet["findings"]["items"])
    constraints = packet["contract"]["constraints"]
    assert any("맞지 않으면 원문을 둔다" in item for item in constraints)
    assert any("없는 정보를 만들어" in item for item in constraints)
    assert len(packet["patterns"]) >= 10
    assert packet == writingPacket(SAMPLE, path="글.md")


def testWritingPacketUsesProjectExemplarAndDocumentRegister():
    config = Config.fromMapping(
        {
            "exemplars": [
                {
                    "rule": "cliche",
                    "before": "조직의 전 문장입니다.",
                    "after": "조직의 후 문장입니다.",
                    "moved": "결론을 직접 씀",
                    "presets": ["blog"],
                }
            ]
        }
    )
    packet = writingPacket(SAMPLE, config)
    cliche = next(entry for entry in packet["guidance"] if entry["rule"] == "cliche")
    assert cliche["exemplar"]["before"] == "조직의 전 문장입니다."
    assert packet["input"]["register"] == "합니다"


def testDraftPacketChangesContractAndCanOmitSource():
    packet = writingPacket("독자는 개발자입니다. 설치 절차를 씁니다.", purpose="draft", includeSource=False)
    assert packet["purpose"] == "draft"
    assert "새 한국어 마크다운 초안" in packet["contract"]["operation"]
    assert any("요구사항 자체를 결과로 고치지 않는다" in item for item in packet["contract"]["constraints"])
    assert "text" not in packet["input"]
    assert packet["verify"]["argv"][1] == "<output.md>"
    rendered = renderWritingPacket(packet)
    assert json.loads(rendered) == packet


def testWritingPacketRejectsUnknownPurpose():
    import pytest

    with pytest.raises(ValueError, match="purpose"):
        writingPacket(SAMPLE, purpose="judge")
