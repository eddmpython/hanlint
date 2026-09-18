"""용례 (usage). 라이선스가 확인된 실제 글에서 낱말이 어떻게 쓰였는지를 든다. 좋은 글을 판정하지 않는다.

- `counts`: 글 종류별 명사 연쇄 빈도표. 패키지에 실린다. nounPile 이 관용 연쇄를 접는 근거다.

fingerprint 와 같은 층 (4) 이다. rules 가 쓰고, analysis 와 config 와 data 만 쓴다.
"""

from __future__ import annotations

from .counts import attested, chainDocuments, usageKindOf, usageTable

__all__ = ["attested", "chainDocuments", "usageKindOf", "usageTable"]
