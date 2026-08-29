"""프로파일 층. 같은 종류의 글들이 실제로 어떤 분포인지를 글 여러 편의 지문에서 만든다.

글쓰기 스킬이 말하는 문체 표본의 기계 판이다. 종류별 프로파일은 기준 말뭉치에서 만들어 hanlint 가 싣고
(`data/profiles.json`), 사용자는 `hanlint profile build 글들/` 로 자기 참조 글의 프로파일을 만든다. 자료형과 읽기는
`data/profiles.py`, 견줌은 규칙 outsideProfile 이다. 사실이지 판정이 아니다.
"""

from __future__ import annotations

from .build import buildProfile

__all__ = ["buildProfile"]
