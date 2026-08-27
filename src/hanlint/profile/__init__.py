"""프로파일 층. 승인된 글들의 지문 분포를 만들고 새 글의 편차 구간을 짚는다.

글쓰기 스킬이 말하는 문체 표본의 기계 판이다. 말투가 남았는가 를 결정적으로 근사한다. 편차는 사실이지
판정이 아니다. 규칙과 형제라 Finding 을 만들지 않고 Deviation 을 낸다. 명령줄이 그것을 notice 로 옮긴다.
"""

from __future__ import annotations

from .build import Profile, buildProfile, loadProfile, saveProfile
from .compare import Deviation, compareToProfile

__all__ = ["Deviation", "Profile", "buildProfile", "compareToProfile", "loadProfile", "saveProfile"]
