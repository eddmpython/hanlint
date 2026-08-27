"""설정과 임계 기본값의 정본.

규칙 함수는 여기서 읽지 자기 안에 숫자를 두지 않는다. 필드 이름이 곧 설정 파일의 키다.

```toml
[tool.hanlint]
disable = ["nounPile"]
analyzer = "surface"
keywordField = "primaryKeyword"
fragmentRun = 3

[tool.hanlint.dictionary]
cliches = ["우리의 여정"]
translationese = [{ pattern = "에 대한 이해", fix = "를 아는 것" }]
```
"""

from __future__ import annotations

from dataclasses import dataclass, field

ANALYZERS = ("surface", "kiwi")


@dataclass
class Config:
    disable: set[str] = field(default_factory=set)
    """끌 규칙 이름."""
    analyzer: str = "surface"
    """분석기. surface 는 의존성 0, kiwi 는 `pip install hanlint[kiwi]` 가 필요하다."""
    keywordField: str | None = None
    """대표 검색어를 읽을 frontmatter 필드. 없으면 keywordMissing 은 돌지 않는다."""
    profile: str | None = None
    """프로파일 파일 경로. 있으면 편차 구간을 notice 로 낸다."""
    dictionary: dict[str, list] = field(default_factory=dict)
    """사전에 더할 항목. 키는 사전 이름 (cliches, translationese, redundantPair, japaneseLoan)."""

    fragmentRun: int = 3
    """한두 문장짜리 문단이 몇 개 이어지면 조각남으로 보는가."""
    introMaxParagraphs: int = 4
    """도입 산문 문단 상한. 스킬: 도입은 문단 넷을 넘지 않는다."""
    headingUniformRatio: float = 0.75
    """H2 끝 글자가 이 비율 넘게 같으면 통일로 본다. 실측: 004 는 8 중 7 이라 0.875 였다."""
    nounPileMin: int = 5
    """명사가 몇 개 이어지면 나열로 보는가. 넷은 `파이썬 데이터프레임 라이브러리` 같은 정상 표현이라 다섯부터."""
    endingRun: int = 4
    """같은 종결어미가 몇 문장 이어지면 반복으로 보는가. im-not-ai E-2 의 4 를 출발점으로."""
    factListMinSentences: int = 3
    """인과 표지 없는 문단을 사실 나열로 보는 최소 문장 수."""
    factListMaxMeanLength: float = 8.0
    """사실 나열로 볼 문단의 평균 어절 수 상한. 긴 문장은 안에서 이미 이어져 있다. 실측: 004 의 오탐 문단은 평균 9~15 어절."""
    topicBreakMinSentences: int = 2
    """화제 중첩 0 을 흐름 끊김으로 볼 때 앞뒤 문단의 최소 문장 수. 한 문장 문단은 중첩이 원래 작다."""

    def enabled(self, ruleName: str) -> bool:
        return ruleName not in self.disable

    @classmethod
    def fromMapping(cls, data: dict) -> Config:
        config = cls()
        for key, value in data.items():
            if key == "disable":
                config.disable = set(value)
            elif key == "analyzer":
                if value not in ANALYZERS:
                    raise ValueError(f"analyzer 는 {' 또는 '.join(ANALYZERS)} 다: {value}")
                config.analyzer = value
            elif key == "dictionary":
                config.dictionary = dict(value)
            elif hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"모르는 설정 키: {key}. hanlint init 이 만드는 파일의 키만 쓴다")
        return config
