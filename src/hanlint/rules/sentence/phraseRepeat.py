from __future__ import annotations

import re
from collections.abc import Iterator
from functools import cache

from ...config import Config
from ...data import loadToml
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule

MIN_SENTENCES = 8
"""산문 문장이 이 수보다 적으면 비율이 튄다. 다섯 문장 가운데 하나가 걸리면 20% 다. 실측에서 분포를 잰
단위와 같은 수를 쓴다."""
MIN_HITS = 2
"""되풀이로 세려면 몇 번 나와야 하는가. 비율만 보면 아홉 문장짜리 글의 한 번이 11% 라 임계를 넘는다.

**한 번은 버릇이 아니다.** 이 조건 없이 만들었다가 규칙이 아홉 문장 가운데 한 번 나온 자리를 짚는 것을 보고
넣었다. 이유 문구가 `한 편에 한 번이면 힘이 있다` 인데 한 번을 짚고 있었다 (2026-09-20)."""


@cache
def entries() -> tuple[tuple[re.Pattern[str], float, str, str, str], ...]:
    """(정규식, 임계 비율, 이름, 이유, 출처). 사전은 data/phraseRepeat.toml 이다."""
    return tuple(
        (re.compile(one["pattern"]), float(one["share"]), one["label"], one["why"], one["source"])
        for one in loadToml("phraseRepeat.toml")
    )


@rule("phraseRepeat", mechanism="repeat")
def phraseRepeat(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """한 글이 같은 문형을 되풀이해 쓰는 경우. 문장 하나하나가 아니라 글 안의 비율로 짚는다.

    왜: `X가 아니라 Y다`는 한 번은 멀쩡한 한국어다. 되풀이하면 글이 같은 소리로 읽힌다. 그래서 한 번 쓴
        것까지 잡으면 바르게 쓴 문장도 잡힌다.
    어디서: 실측. 사람 글 4,021편(위키백과 본문 1,642, 지침 931, 토론 1,304, 사업보고서 144)과 기계 글 360편에서
        문서마다 비율을 재서, 사람 글 100편 가운데 99편이 넘지 않는 값보다 높게 기준값을 잡았다. 사람 글은
        100편 가운데 99편이 3.4% 이하이고(두 번 이상 나온 것만 셀 때), 기준값 8%에서는 사람 글 0.17%, 기계 글 20%가
        걸린다. 사전과 기준값은 data/phraseRepeat.toml에 있다. 문형은 두 말뭉치를 비교해 찾았다(1,000문장당 사람
        7.05, 기계 65.55). `~하는 편이 낫다`는 후보였다가 두 번 이상 나온 글로 세면 기계 글이 1%만 걸려 뺐다.
    고치기: 되풀이된 문장 가운데 덜 필요한 것을 바로 말하는 문장으로 바꾼다. 한 편에 한 번은 남겨도 된다.
        걸린 문장은 전부 센다. 지적은 하나지만 이유에 줄 번호를 모두 적는다. 하나만 인용하면 고치는 쪽이
        나머지를 정규식으로 다시 찾아야 한다. 한 줄에 여러 문장이 있으면 그 줄은 한 번만 적는다.
    안 잡는 것: 산문 문장이 8개보다 적은 글. 종결어미가 없는 줄(제목, 항목명, 표의 칸). 기준값 이하의 되풀이.
        두 번보다 적게 나온 문형: 한 번 쓴 글은 비율이 기준값을 넘어도 잡지 않는다. 겉으로 보이는 글자로
        어림하는 규칙이라 경고로 낸다.
    """
    prose = [one for one in doc.sentences if one.length > 0 and one.ending != "없음"]
    if len(prose) < MIN_SENTENCES:
        return
    for pattern, share, label, why, source in entries():
        hit = [one for one in prose if pattern.search(one.text)]
        if len(hit) < MIN_HITS or len(hit) / len(prose) <= share:
            continue
        lines = ", ".join(str(one) for one in sorted({one.line for one in hit}))
        cited = f" ({source})" if source else ""
        yield Finding(
            "phraseRepeat",
            hit[0].line,
            hit[0].text,
            f"`{label}` 문형이 산문 {len(prose)}문장 가운데 {len(hit)}번({lines}줄) 나와 상한 {share:.0%}를 넘는다. {why}{cited}",
            None,
            NOTICE,
            DOCUMENT,
            -1,
        )
