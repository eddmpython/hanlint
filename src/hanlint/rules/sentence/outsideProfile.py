from __future__ import annotations

from collections.abc import Iterator

from ...config import PROFILE_OF, Config
from ...data.profiles import Profile, profileOf, userProfile
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, SENTENCE, Finding
from ..registry import rule

FEATURES = (
    ("length", "문장 길이", "어절"),
    ("commas", "쉼표", "개"),
    ("newTopics", "처음 나온 화제어", "개"),
    ("hedges", "헤지 표현", "개"),
)
"""대조하는 문장 지표와 지적문의 이름과 단위. 의 와 명사 연속은 euiChain 과 nounPile 이 임계로 따로 본다."""


def profileFor(config: Config) -> Profile | None:
    """사용자 프로파일이 있으면 그것, 없으면 프리셋이 가리키는 종류의 프로파일. 둘 다 없으면 None."""
    if config.profile:
        return userProfile(config.profile)
    kind = PROFILE_OF.get(config.preset)
    return profileOf(kind) if kind else None


def shareText(permille: int) -> str:
    return "0.1% 아래" if permille == 0 else f"{permille // 10}.{permille % 10}%"


@rule("outsideProfile", mechanism="threshold")
def outsideProfile(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """같은 종류의 글에서 백 문장에 하나도 안 되는 값 (문장 길이, 쉼표, 처음 나온 화제어, 헤지) 을 가진 문장.

    왜: 독자는 그 종류의 글에서 늘 보던 만큼을 기대한다. 편집된 글 수천 문장 가운데 1% 도 안 되는 길이나 새 화제어
        수는 그 독자가 그 종류에서 겪지 않던 부담이다. 좋다 나쁘다가 아니라 자리가 어디인지를 말한다.
    어디서: 실측. 기준 말뭉치 390편에서 30어절을 넘는 문장이 안내서 0.16%, 기술 문서 0.87%, 뉴스 6.7%, 1930년대 수필
        8.3% 였다. 임계 하나가 종류마다 열 배씩 다르게 잡는다 (2026-08-29). 종류별 norms 를 백분위로 보이는 것은
        Coh-Metrix 가 영어에서 한 방식이고 한국어에는 없었다. 프로파일은 data/profiles.json (scripts/buildProfiles.py
        가 corpus/catalogue.toml 의 말뭉치에서 만든다). 백분위 임계는 config.profilePercentile. 처음 나온 화제어는 독자
        상태 (fingerprint/readerState.py) 의 known 으로 센다.
    고치기: 문장을 나누거나 쉼표 절을 문장으로 세운다. 처음 나온 화제어가 많으면 앞 문장에서 하나씩 먼저 세운다.
        헤지는 수치나 조건으로 바꾼다.
    안 잡는 것: 프리셋에 프로파일이 없는 종류. 99% 값이 0 인 지표 (거의 안 나오는 것은 하나만 있어도 꼬리라 짚을 것이
        없다). 상위 1% 는 정의상 백 문장에 하나라 notice 로만 낸다. `--profile` 이
        가리키는 사용자 프로파일이 있으면 종류 대신 그것과 견준다.
    """
    profile = profileFor(config)
    if profile is None:
        return
    p = config.profilePercentile
    for sentence in doc.sentences:
        known = doc.reader.beforeSentence[sentence.index].known
        values = {
            "length": sentence.length,
            "commas": sentence.commas,
            "newTopics": len(sentence.topics - known),
            "hedges": sentence.hedges,
        }
        for key, label, unit in FEATURES:
            hist = profile.sentence.get(key)
            if hist is None or p not in hist.percentiles:
                continue
            limit = hist.percentile(p)
            value = values[key]
            # 99% 값이 0 이면 (헤지처럼 거의 안 나오는 지표) 하나만 있어도 꼬리다. 그런 자리는 짚을 것이 없다.
            if limit == 0 or value <= limit:
                continue
            yield Finding(
                "outsideProfile",
                sentence.line,
                sentence.text,
                f"{label} {value}{unit}. {profile.label} {profile.sentences}문장 가운데 상위 "
                f"{shareText(hist.shareAtOrAbove(value))}다. {p}%는 {limit}{unit} 이하다",
                None,
                NOTICE,
                SENTENCE,
                sentence.index,
            )
