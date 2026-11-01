from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.markers import matchedTexts
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("bridgeRepeat", mechanism="repeat")
def bridgeRepeat(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """절을 닫는 문장이 이음말(`이번에는`, `이제`, `다음으로`)로 시작하는 절이 3개 이상인 글.

    왜: 절 끝에서 다음 절을 예고하는 문장은 한 번이면 두 절을 잇지만, 절마다 되풀이되면 틀에 박힌 글이 된다.
        독자는 절이 남긴 결과가 아니라 `이번에는`이라는 말만 거듭 읽게 되고, 절 사이에 실제 순서가 있는지 없는지가
        그 말에 가려진다.
    어디서: 실제 강의 글 여섯 편에서 `앞에서 A 를 확인했습니다. 이번에는 B 를 확인합니다`가 53번 나왔고, 그중 한
        편은 14절 가운데 12절이 이 말로 끝났다. 기준 말뭉치 390편에서 문장 첫머리의 `이번에는`은 1건이었다. 강의
        글은 `앞에서 ... 이번에는 ...`을 되풀이해 없는 순서를 만들지 않는다는 쓰기 방식에서 왔다. 이음말 목록은
        data/bridgeOpeners.txt에 있고, 기준값은 설정 bridgeRepeatMin(기본 3)이다.
    고치기: 절이 방금 만든 결과를 이름으로 부르고 그것이 아직 못 하는 일을 한 문장으로 적는다. 그 못 하는 일이
        다음 절의 제목이 된다. 나란히 놓인 사례라면 억지로 잇지 말고 같은 기준 아래의 사례라고 밝힌다.
    안 잡는 것: 이음말로 끝나는 절이 기준값보다 적은 글, 문장 중간의 `이번에는`, 절의 마지막 산문 문단이 아닌 곳,
        도입 절은 잡지 않는다. 절 끝이 코드나 표라도 그 앞 산문 문단의 마지막 문장을 본다.
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
        f"절 {len(closers)}개가 `{', '.join(markers)}` 같은 이음말로 시작하는 문장으로 끝난다. "
        "예고가 절마다 되풀이되면 틀에 박힌 글이 된다. 방금 만든 결과를 이름으로 부르고 아직 못 하는 일을 적는다",
        None,
        "error",
        DOCUMENT,
        -1,
    )
