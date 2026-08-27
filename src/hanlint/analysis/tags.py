"""Kiwi 형태소 태그 묶음. 태그 이름은 외부 명칭이라 원어 그대로다.

NNG 일반명사, NNP 고유명사, SL 외국어, SH 한자, XPN 접두사, XSN 명사 파생 접미사, JKG 관형격 조사,
VV 동사, XSV 동사 파생 접미사, EC 연결어미, VX 보조용언.
"""

from __future__ import annotations

NOUN_TAGS = frozenset({"NNG", "NNP", "SL", "SH", "XPN", "XSN"})
"""명사 나열에서 명사로 치는 태그. 접두사와 접미사는 명사에 붙어 하나의 덩어리를 이룬다."""

FOREIGN_TAG = "SL"
"""외국어. 이어지면 영어 구절 하나라 명사 나열에서 한 덩어리로 센다."""

GENITIVE_TAG = "JKG"
"""관형격 조사 `의`."""

PASSIVE_STEM_TAGS = frozenset({"VV", "XSV"})
"""`되` 가 올 수 있는 태그."""

CONNECTIVE_TAG = "EC"
AUXILIARY_TAG = "VX"
PASSIVE_CONNECTIVES = frozenset({"어", "아", "여"})
