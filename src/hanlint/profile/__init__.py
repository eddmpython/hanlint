"""프로파일 부분. 같은 종류의 글들이 실제로 어떤 분포인지를 글 여러 편의 분석 결과에서 만든다.

사람이 문체 표본을 보고 따라 쓰는 일을 기계가 수치로 하는 것이다. 종류별 프로파일은 기준 말뭉치에서 만들어 hanlint가 싣고
(`data/profiles.json`), 사용자는 `hanlint profile build 글들/`로 자기 참조 글의 프로파일을 만든다. 자료형과 읽기는
`data/profiles.py`, 비교는 규칙 outsideProfile이 한다. 센 사실이지 판정이 아니다.
"""

from __future__ import annotations

from .build import buildProfile

__all__ = ["buildProfile"]
