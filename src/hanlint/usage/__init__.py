"""용례(usage). 라이선스가 확인된 실제 글에서 단어가 어떻게 쓰였는지를 든다. 좋은 글을 판정하지 않는다.

- `counts`: 글 종류별 명사 연쇄 빈도표. 패키지에 실린다. nounPile이 관용 연쇄를 접는 근거다.
- `sentences`: 글 종류별 문장 역인덱스. 사용자 기계에만 있다. `hanlint usage`가 BM25로 문장을 보인다.

fingerprint와 같은 단계(4)다. rules와 cli가 이 부분을 쓰고, 이 부분은 analysis와 config와 data만 쓴다.
"""

from __future__ import annotations

from .counts import attested, chainDocuments, conventional, patternDocuments, usageKindOf, usageTable
from .sentences import (
    BuildResult,
    Collocation,
    Hit,
    UsageIndex,
    buildIndex,
    indexTokens,
    listIndexes,
    loadIndex,
    queryCores,
    readDocuments,
)
from .sentences import defaultRoot as defaultUsageRoot

__all__ = [
    "BuildResult",
    "Collocation",
    "Hit",
    "UsageIndex",
    "attested",
    "buildIndex",
    "chainDocuments",
    "conventional",
    "defaultUsageRoot",
    "indexTokens",
    "listIndexes",
    "loadIndex",
    "patternDocuments",
    "queryCores",
    "readDocuments",
    "usageKindOf",
    "usageTable",
]
