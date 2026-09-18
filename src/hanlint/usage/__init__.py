"""용례 (usage). 라이선스가 확인된 실제 글에서 낱말이 어떻게 쓰였는지를 든다. 좋은 글을 판정하지 않는다.

- `counts`: 글 종류별 명사 연쇄 빈도표. 패키지에 실린다. nounPile 이 관용 연쇄를 접는 근거다.
- `sentences`: 글 종류별 문장 역인덱스. 사용자 기계에만 있다. `hanlint usage` 가 BM25 로 문장을 보인다.

fingerprint 와 같은 층 (4) 이다. rules 와 cli 가 쓰고, analysis 와 config 와 data 만 쓴다.
"""

from __future__ import annotations

from .counts import attested, chainDocuments, usageKindOf, usageTable
from .sentences import BuildResult, Hit, UsageIndex, buildIndex, indexTokens, loadIndex, readDocuments
from .sentences import defaultRoot as defaultUsageRoot

__all__ = [
    "BuildResult",
    "Hit",
    "UsageIndex",
    "attested",
    "buildIndex",
    "chainDocuments",
    "defaultUsageRoot",
    "indexTokens",
    "loadIndex",
    "readDocuments",
    "usageKindOf",
    "usageTable",
]
