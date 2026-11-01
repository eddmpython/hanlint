from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("hardWord", mechanism="dictionary")
def hardWord(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """`금일`, `익월`, `금회`처럼 행정 한자어를 더 익숙한 말로 바꿀 수 있는지 살펴볼 곳.

    왜: 평소에 쓰지 않는 말은 독자가 머릿속에서 한 번 번역한다. 같은 뜻이면 더 자주 쓰는 말로 바로 쓴다.
    어디서: 국립국어원 다듬은 말(korean.go.kr 개선 > 다듬은 말)과 표준국어대사전의 동의어 정보. 사전은
        data/easyWords.toml이고 항목마다 출처가 있다. 자료에 대신 쓸 말이 있어도 분야 용어와 외래어는
        문맥에 따라 뜻이 달라져 기본 사전에서 뺐다. 사용자는 설정의 dictionary.easyWords로 더한다.
    고치기: 제안이 독자에게 더 익숙하고 원문의 뜻도 지킬 때만 고른다. 널리 쓰는 기술 용어는 남기고 필요한
        뜻을 문장으로 설명한다. 단어를 직역해 새 이름을 만들지 않는다. `hanlint fix`는 고치지 않는다.
    안 잡는 것: 사전에 없는 말. 고유명사와 제품 이름. 백틱과 따옴표 안의 인용. 제안이라 확인 권고로만 낸다.
        그 종류의 글이 거의 다 쓰는 말은 짚지 않는다. 프리셋이 정한 종류의 문서 90% 이상(설정 usageShare)에
        나온 사전 항목이다.
    """
    yield from dictionaryFindings(doc, "easyWords", "hardWord", NOTICE, config=config)
