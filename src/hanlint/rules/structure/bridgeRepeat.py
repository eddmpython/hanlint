from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.markers import matchedTexts
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("bridgeRepeat")
def bridgeRepeat(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """절을 닫는 문장이 이음 표지 (이번에는, 이제, 다음으로) 로 시작하는 절이 bridgeRepeatMin 개 이상인 글.

    왜: 절 끝에서 다음 절을 예고하는 문장은 한 번이면 이음이고 절마다 되풀이되면 틀이다. 독자는 절이 남긴 결과가
        아니라 `이번에는` 이라는 신호음을 읽게 되고, 절 사이에 실제 순서가 있는지 없는지가 그 소리에 가려진다.
    어디서: 실측. eddmpython-course 의 강의 여섯 편에서 `앞에서 A 를 확인했습니다. 이번에는 B 를 확인합니다` 가
        53번 나왔고 03 은 14절 가운데 12절이 이 틀로 닫혔다. 기준 말뭉치 390편에서 문장 첫머리 `이번에는` 은
        1건이다. 글쓰기 스킬의 강의 교안 쓰기, `앞에서 ... 이번에는 ...` 을 반복해서 없는 순서를 만들지 않는다.
        표지 목록은 data/bridgeOpeners.txt, 임계는 config.bridgeRepeatMin.
    고치기: 절이 방금 만든 결과를 이름으로 부르고 그것이 아직 못 하는 일을 한 문장으로 적는다. 그 못 하는 일이
        다음 절의 제목이 된다. 병렬 사례라면 억지로 잇지 말고 같은 기준 아래의 사례라고 밝힌다.
    안 잡는 것: 이음 표지로 닫히는 절이 임계 아래인 글. 문장 중간의 이번에는. 절의 마지막 산문 문단이 아닌 자리.
        도입 절. 절 끝이 코드나 표라도 그 앞 산문 문단의 마지막 문장을 본다.
    """
    closers: list[tuple] = []
    for section in doc.bodySections:
        if not section.paragraphs:
            continue
        sentences = section.paragraphs[-1].sentences
        if not sentences:
            continue
        found = matchedTexts(sentences[-1].text, "bridgeOpeners.txt")
        if found:
            closers.append((sentences[-1], found[0]))
    if len(closers) < config.bridgeRepeatMin:
        return
    markers = sorted({marker for _, marker in closers})
    first = closers[0][0]
    yield Finding(
        "bridgeRepeat",
        first.line,
        first.text,
        f"절 {len(closers)}개가 `{', '.join(markers)}` 같은 이음 표지로 시작하는 문장으로 닫힌다. "
        "예고가 절마다 되풀이되면 틀이다. 방금 만든 결과를 이름으로 부르고 아직 못 하는 일을 적는다",
        None,
        "error",
        DOCUMENT,
        -1,
    )
