"""사동과 피동의 겹을 표층에서 확정되는 만큼만 분해한다.

기준 말뭉치 17,420문장에서 이중 피동 24건과 `-게 만들다` 사동 21건이 나왔다. 피동은
`passiveStems.txt`에 있는 접미 피동사와 `되다` 뒤에 `-어지다`가 다시 붙은 경우만 분해한다.
`만들어지다`처럼 첫 어간이 피동사 목록에 없으면 단순 피동이므로 건드리지 않는다.

`-게 만들다`는 사동 표지 둘을 분해하지만 대체 문장을 만들지 않는다. `쉽게 만들다`가 `쉽게 하다`인지,
주어를 바꿔 `쉬워지다`로 쓸지는 뜻이 정한다. 형태 층은 그 선택을 하지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

from ...data import loadLines

PASSIVE = "피동"
CAUSATIVE = "사동"
CAUSATIVE_FORM = re.compile(r"^(?P<base>[가-힣]+)게\s+만들(?P<tail>[가-힣]*)$")
CONTRACTION = {"이": "여", "히": "혀", "리": "려", "기": "겨"}


@dataclass(frozen=True)
class VoiceForm:
    surface: str
    kind: str
    base: str
    markers: tuple[str, ...]
    reduced: str | None
    """뜻을 고르지 않고 형태만으로 하나로 줄일 수 있는 꼴. 사동은 None이다."""


@cache
def passiveLinks() -> dict[str, str]:
    """`보여지` 같은 표층 겹을 첫 피동 어간 `보이`로 잇는 표."""
    links = {"되어지": "되"}
    for stem in loadLines("passiveStems.txt"):
        last = stem[-1]
        linked = stem[:-1] + CONTRACTION[last] if last in CONTRACTION else stem + "어"
        links[linked + "지"] = stem
    return links


def decomposePassive(surface: str) -> VoiceForm | None:
    base = passiveLinks().get(surface)
    if base is None:
        return None
    return VoiceForm(surface, PASSIVE, base, ("접미 피동", "어지"), base)


def decomposeCausative(surface: str) -> VoiceForm | None:
    match = CAUSATIVE_FORM.match(surface)
    if not match:
        return None
    return VoiceForm(surface, CAUSATIVE, match.group("base"), ("게", "만들"), None)


def decomposeVoice(surface: str) -> VoiceForm | None:
    """확정되는 이중 피동이나 분석적 사동이면 그 겹. 아니면 None."""
    return decomposePassive(surface) or decomposeCausative(surface)
