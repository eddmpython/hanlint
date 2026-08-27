from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("spacing")
def spacing(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """할수 있다, 것같다, 떠난지 3년, 한번도, 두번, 수 밖에, 뿐만아니라 처럼 자주 틀리는 띄어쓰기.

    왜: 의존 명사와 단위 명사는 띄고 조사는 붙인다는 규칙이 가장 자주 무너지는 자리다. 틀리면 독자가
        낱말 경계를 다시 세운다.
    어디서: 국립국어원 한글 맞춤법 제5장 띄어쓰기 (제41항 조사, 제42항 의존 명사, 제43항 단위 명사).
        항목마다 근거가 붙어 있다 (data/spacing.toml). 관형형 ㄹ 뒤의 의존 명사는 받침 부류 {ㄹ} 로 잡는다.
    고치기: 항목마다 띄거나 붙인 꼴을 fix 로 낸다. hanlint fix 가 적용한다.
    안 잡는 것: 뿐, 만큼, 대로 (체언 뒤 조사와 관형형 뒤 의존 명사를 표층으로 가르지 못한다). 못하다/못 하다,
        안되다/안 되다 (뜻이 갈린다). 실수, 술수 처럼 ㄹ 받침 명사 뒤의 수. 백틱과 따옴표 안의 인용.
    """
    yield from dictionaryFindings(doc, "spacing", "spacing")
