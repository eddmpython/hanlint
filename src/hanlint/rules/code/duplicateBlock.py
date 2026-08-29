from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule

MIN_LINES = 4


def similarity(a: list[str], b: list[str]) -> float:
    """줄 다중집합의 겹침 비. 2 * 공통 / (a + b)."""
    if not a or not b:
        return 0.0
    counts = Counter(a)
    common = 0
    for line in b:
        if counts[line] > 0:
            counts[line] -= 1
            common += 1
    return 2 * common / (len(a) + len(b))


@rule("duplicateBlock", mechanism="repeat")
def duplicateBlock(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """앞선 코드나 출력 블록과 거의 같은 블록.

    왜: 서른 줄 가운데 한 줄만 다른 블록을 두 번 읽으면 독자는 다른 한 줄을 찾느라 표를 훑는다. 다른 줄만 보이거나
        앞 블록을 가리키는 것이 낫다.
    어디서: 실측. 블로그 004 에서 두 엔진의 출력 서른 줄 가운데 다른 것은 한 줄이었고 사람 평가자가 집었다.
        임계는 config.duplicateBlockRatio, 최소 줄 수는 넷.
    고치기: 다른 줄만 남기고 나머지는 앞 블록을 가리킨다. 정말 둘 다 필요하면 무엇이 다른지 산문에서 먼저 말한다.
    안 잡는 것: 넉 줄 미만 블록. 종류가 다른 블록 (코드와 출력). 임계 아래. notice 로만 낸다.
    """
    blocks = [b for b in doc.codeBlocks if len([line for _, line in b.lines if line.strip()]) >= MIN_LINES]
    for later in range(len(blocks)):
        current = blocks[later]
        currentLines = [line.strip() for _, line in current.lines if line.strip()]
        for earlier in range(later):
            previous = blocks[earlier]
            if previous.isOutput != current.isOutput:
                continue
            ratio = similarity([line.strip() for _, line in previous.lines if line.strip()], currentLines)
            if ratio >= config.duplicateBlockRatio:
                yield Finding(
                    "duplicateBlock",
                    current.startLine,
                    currentLines[0],
                    f"{previous.startLine}번째 줄의 블록과 {ratio:.0%} 같다. 다른 줄만 남기거나 앞 블록을 가리킨다",
                    None,
                    NOTICE,
                    DOCUMENT,
                    current.index,
                )
                break
