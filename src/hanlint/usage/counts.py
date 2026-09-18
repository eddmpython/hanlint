"""명사 연쇄 빈도표. 글 종류마다 `data/usageCounts.<종류>.json` 하나이고 값은 그 연쇄가 나온 문서 수다.

연쇄의 뜻은 analysis/tokenize.py 의 nounRuns 가 소유한다. 표의 키는 그 어절들을 빈칸 하나로 이은 것이라 규칙이 같은
함수로 뽑은 연쇄를 그대로 찾는다. 표는 scripts/derive/usageCounts.py 가 말뭉치에서 만들고 손으로 고치지 않는다.
문서 수를 세는 까닭: 한 회사가 한 보고서에서 같은 말을 백 번 써도 그 회사의 버릇이지 관용이 아니다.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache

from ..config import USAGE_OF, Config
from ..data.load import loadJson


def usageKindOf(config: Config) -> str | None:
    """이 설정이 볼 빈도표의 종류. usageKind 가 None 이면 프리셋이 정하고 "" 면 보지 않는다."""
    kind = USAGE_OF.get(config.preset) if config.usageKind is None else config.usageKind
    return kind or None


@cache
def usageTable(kind: str) -> dict:
    """표 전체 (kind, source, documents, minLength, minDocuments, chains)."""
    return loadJson(f"usageCounts.{kind}.json")


def chainDocuments(chain: Sequence[str], kind: str) -> int:
    """이 연쇄가 그 종류의 말뭉치에서 몇 편의 문서에 나왔나. 표에 없으면 0."""
    return usageTable(kind)["chains"].get(" ".join(chain), 0)


def attested(chain: Sequence[str], kind: str, minimum: int) -> bool:
    """연쇄가 minimum 편 이상의 문서에 나왔으면 그 종류의 관용이다."""
    return chainDocuments(chain, kind) >= minimum
