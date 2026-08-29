from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("hardWord", mechanism="dictionary")
def hardWord(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """금일, 익월, 상기, 소정의, 노하우, 인프라, 피드백 처럼 쉬운 말이 있는 어려운 한자어와 외래어.

    왜: 평소에 쓰지 않는 말은 독자가 머릿속에서 한 번 번역한다. 같은 뜻이면 더 자주 쓰는 말로 바로 쓴다.
        글쓰기 스킬의 쉬운 말로 바로 쓰기 다.
    어디서: 국립국어원 다듬은 말 (korean.go.kr 개선 > 다듬은 말) 과 표준국어대사전의 동의어 정보. 사전은
        data/easyWords.toml 이고 항목마다 출처가 있다. 사용자는 설정의 dictionary.easyWords 로 더한다.
    고치기: 항목마다 쉬운 말을 fix 로 제안한다. 문맥에 따라 다른 말이 맞을 수 있어 hanlint fix 는 적용하지
        않고 사람이 고른다.
    안 잡는 것: 사전에 없는 말. 고유명사와 제품 이름. 백틱과 따옴표 안의 인용. 전문 용어가 정확해서 꼭
        필요한 자리 (그때는 이 규칙을 끄거나 인라인 제어로 그 문단만 끈다). 제안이라 notice 로만 낸다.
    """
    yield from dictionaryFindings(doc, "easyWords", "hardWord", NOTICE)
