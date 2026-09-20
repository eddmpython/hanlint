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
    """한 글이 같은 문형 수법에 기대는 자리. 낱낱이 아니라 글 안의 비율로 짚는다.

    왜: `X가 아니라 Y다` 는 한 번은 멀쩡한 한국어다. 되풀이될 때 버릇이 되고 글이 같은 소리로 읽힌다.
        그래서 낱낱으로 짚으면 정당한 용법을 때린다.
    어디서: 실측. 사람 글 4,021편 (위키백과 본문 1,642, 지침 931, 토론 1,304, 사업보고서 144) 과 기계 글
        360편의 문서별 분포를 재서 사람 99분위 위를 임계로 잡았다. 사람 99분위가 3.4% (2회 이상 기준) 이고
        임계 8% 에서 사람 0.17%, 기계 20% 가 걸린다. 사전과 임계는 data/phraseRepeat.toml, 잰 것은
        tests/_attempts/aiTells/ 다. 꼴 자체는 두 말뭉치를 대조해 캤다 (천문장당 사람 7.05 대 기계 65.55).
        `~하는 편이 낫다` 는 후보였다가 2회 조건에서 기계 1% 만 걸려 뺐다.
    고치기: 되풀이된 자리 가운데 힘이 덜한 것을 곧은 문장으로 바꾼다. 한 편에 한 번은 남겨도 된다.
    안 잡는 것: 산문 문장이 MIN_SENTENCES 개 아래인 글. 종결어미가 없는 줄 (제목, 항목명, 표의 칸). 임계 아래의
        되풀이. **MIN_HITS 번 미만**. 한 번 쓴 글은 비율이 임계를 넘어도 조용하다. 표층 근사라 notice 다.
    """
    prose = [one for one in doc.sentences if one.length > 0 and one.ending != "없음"]
    if len(prose) < MIN_SENTENCES:
        return
    for pattern, share, label, why, source in entries():
        hit = [one for one in prose if pattern.search(one.text)]
        if len(hit) < MIN_HITS or len(hit) / len(prose) <= share:
            continue
        yield Finding(
            "phraseRepeat",
            hit[0].line,
            hit[0].text,
            f"`{label}` 꼴이 산문 {len(prose)}문장 가운데 {len(hit)}번이다 (상한 {share:.0%}). {why} ({source})",
            None,
            NOTICE,
            DOCUMENT,
            -1,
        )
