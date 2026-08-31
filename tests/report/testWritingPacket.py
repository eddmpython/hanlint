import json
from hashlib import sha256

from hanlint import Config, WritingBrief, writingPacket
from hanlint.report import renderWritingPacket

SAMPLE = """# 속도 보고

핵심은 처리 속도입니다. 설계에 대한 이해가 필요합니다.

## 결과

파일을 엽니다. 결과가 보일까요? 표에 3초라고 나옵니다.
"""


def testWritingPacketCarriesEvidenceWithoutInjectingGeneralExamples():
    packet = writingPacket(SAMPLE, path="글.md")
    assert packet["version"] == 2 and packet["kind"] == "hanlint.writingPacket" and packet["purpose"] == "revise"
    assert packet["input"]["text"] == SAMPLE and packet["input"]["preset"] == "blog"
    # 길이만 재면 빈 문자열 해시로 굳혀도 초록이다. 값으로 못박는다 (2026-08-31).
    assert packet["input"]["textSha256"] == sha256(SAMPLE.encode()).hexdigest()
    assert packet["comparison"]["referenceProfile"]["source"] == "bundled:blog"
    assert packet["comparison"]["current"]["sentenceCount"] == 5
    assert packet["comparison"]["readerState"]["numbersSeen"] == ["3"]
    assert packet["findings"]["errorCount"] > 0
    assert packet["guidance"] == []
    assert all("exemplar" not in finding for finding in packet["findings"]["items"])
    constraints = packet["contract"]["constraints"]
    assert any("다른 본보기를 끌어오지 말고" in item for item in constraints)
    assert any("없는 정보를 만들어" in item for item in constraints)
    assert any("결과 글의 사실이나 문장 재료로 옮기지 않는다" in item for item in constraints)
    assert "patterns" not in packet
    assert "자연스러움" in packet["verify"]["meaning"] and "보장하지 않" in packet["verify"]["meaning"]
    assert packet == writingPacket(SAMPLE, path="글.md")


def testWritingPacketUsesOnlyAnExactlyMatchedApprovedPatch():
    config = Config.fromMapping(
        {
            "patches": [
                {
                    "rule": "cliche",
                    "before": "핵심은 처리 속도입니다.",
                    "after": "처리에는 3초가 걸립니다.",
                    "moved": "결론을 직접 씀",
                    "cue": "핵심은",
                    "reader": "new",
                    "presets": ["blog"],
                }
            ]
        }
    )
    packet = writingPacket(SAMPLE, config)
    cliche = next(entry for entry in packet["guidance"] if entry["rule"] == "cliche")
    assert cliche["patch"]["before"] == "핵심은 처리 속도입니다."
    assert cliche["patch"]["match"] == {
        "sourceText": "핵심은 처리 속도입니다.",
        "sentence": "핵심은 처리 속도입니다.",
        "preset": "blog",
        "cue": "핵심은",
        "reader": "new",
    }
    assert not any(entry["rule"] == "translationese" for entry in packet["guidance"])
    assert packet["input"]["register"] == "합니다"
    assert writingPacket(SAMPLE, config, purpose="draft")["guidance"] == []


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


def testStructuredBriefBecomesAnIsolatedDraftPacket():
    brief = WritingBrief.fromMapping(
        {
            "version": 1,
            "preset": "docs",
            "reader": "처음 쓰는 작성자",
            "task": "명령을 실행한다",
            "facts": [{"id": "F1", "statement": "명령은 `mora check`이고 종료 코드는 0이다."}],
            "mustInclude": ["`mora check`", "종료 코드는 0"],
            "allowedNumbers": ["0"],
            "forbidden": [],
            "length": {"min": 100, "max": 300},
        }
    )
    packet = writingPacket(brief, path="brief.json", purpose="draft")
    assert packet["input"]["brief"] == brief.asDict()
    assert packet["input"]["briefSha256"] == brief.digest
    assert "comparison" not in packet and packet["findings"]["items"] == []
    assert packet["verify"]["argv"][:3] == ["hanlint", "guard", "brief.json"]
    assert "보장하지 않는다" in packet["contract"]["completion"][-1]
    assert writingPacket(brief.asDict(), purpose="draft", includeSource=False)["input"].get("brief") is None

    defaultPacket = writingPacket(brief, purpose="draft")
    strategyPacket = writingPacket(brief, purpose="draft", strategy="rhetoricalBlueprintV1")
    assert "strategy" not in defaultPacket
    assert strategyPacket["strategy"]["input"]["briefSha256"] == brief.digest
    assert strategyPacket["strategy"]["reference"]["corpus"]["containsSourceText"] is False
    assert len(strategyPacket["contract"]["constraints"]) == len(defaultPacket["contract"]["constraints"]) + 2
    encoded = json.dumps(
        writingPacket(brief, path="brief.json", purpose="draft"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    assert sha256(encoded.encode()).hexdigest() == "eafc7ab19dd86582f7b1614670e2a4adf1384023be157ef9c49e50cf68d79b9c"


def testStructuredBriefRejectsRevisionPurpose():
    brief = {
        "version": 1,
        "preset": "blog",
        "reader": "독자",
        "task": "결정한다",
        "facts": [{"id": "F1", "statement": "값은 3이다."}],
        "mustInclude": ["값은 3"],
        "allowedNumbers": ["3"],
        "forbidden": [],
        "length": {"min": 10, "max": 100},
    }
    import pytest

    with pytest.raises(ValueError, match="purpose draft"):
        writingPacket(brief)

    with pytest.raises(ValueError, match="구조화 writing brief"):
        writingPacket("자유 형식 요구", purpose="draft", strategy="rhetoricalBlueprintV1")


def testWritingPacketCarriesOnlyOneSafeSurfaceOperation():
    config = Config.fromMapping({"operations": [{"before": "렌더", "after": "렌더링", "presets": ["blog"]}]})
    packet = writingPacket("첫 렌더 결과입니다.", config)
    assert packet["guidance"] == [
        {
            "line": 1,
            "operation": {
                "kind": "surfaceSubstitution",
                "before": "렌더",
                "after": "렌더링",
                "sourceText": "첫 렌더 결과입니다.",
                "result": "첫 렌더링 결과입니다.",
                "match": {"preset": "blog", "unique": True, "wordBoundary": True, "protectedFacts": True},
            },
        }
    ]
    assert writingPacket("렌더 뒤 렌더 결과입니다.", config)["guidance"] == []
    assert writingPacket("첫 렌더 결과입니다.", config, purpose="draft")["guidance"] == []
    protected = Config.fromMapping(
        {
            "operations": [{"before": "렌더", "after": "렌더링", "presets": ["blog"]}],
            "protectedTerms": ["렌더"],
        }
    )
    assert writingPacket("첫 렌더 결과입니다.", protected)["guidance"] == []


def testExactPatchKeepsPriorityOverSurfaceOperation():
    source = "핵심은 렌더입니다."
    config = Config.fromMapping(
        {
            "patches": [
                {
                    "rule": "cliche",
                    "before": source,
                    "after": "렌더링에는 3초가 걸립니다.",
                    "moved": "결과를 직접 씀",
                    "cue": "핵심은",
                    "reader": "new",
                    "presets": ["blog"],
                }
            ],
            "operations": [{"before": "렌더", "after": "렌더링", "presets": ["blog"]}],
        }
    )
    guidance = writingPacket(source, config)["guidance"]
    assert len(guidance) == 1 and "patch" in guidance[0]
