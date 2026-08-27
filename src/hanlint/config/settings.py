"""설정과 임계 기본값의 정본.

규칙 함수는 여기서 읽지 자기 안에 숫자를 두지 않는다. 필드 이름이 곧 설정 파일의 키다.

```toml
[tool.hanlint]
preset = "blog"
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

PRESETS: dict[str, tuple[str, ...]] = {
    "blog": (),
    "report": ("noQuestion", "readerAbsent", "sectionResult", "firstResultDistance", "introImage", "moreLater"),
    "docs": (
        "noQuestion",
        "readerAbsent",
        "sectionResult",
        "firstResultDistance",
        "introImage",
        "moreLater",
        "draftHistory",
        "blockUnread",
    ),
}
"""글의 종류마다 처음부터 끄고 시작할 규칙. `preset` 키가 고르고 `disable` 이 그 위에 더한다.

blog 는 전부 켠다. 독자를 부르고 절마다 결과를 남기는 글이 기준이다.
report 는 보고서다. 독자에게 말을 걸지 않고 절이 결과를 남기지 않으며 도입이 짧을 필요가 없다.
docs 는 참고 문서와 명세다. report 에 더해 검증 사실을 남기는 것 (draftHistory) 과 그림을 text 펜스로
그리는 것 (blockUnread) 이 제 일이다. 실측: 이 저장소의 hanlint.toml 이 noQuestion 과 readerAbsent 를
손으로 끄고 있었다. 프리셋은 그 손질을 이름 하나로 바꾼 것이다.
"""

PRESET_NAMES = tuple(PRESETS)


@dataclass
class Config:
    preset: str = "blog"
    """글의 종류. PRESETS 가 정한 규칙을 처음부터 끈다. disable 은 그 위에 더한다."""
    disable: set[str] = field(default_factory=set)
    """끌 규칙 이름."""
    analyzer: str = "surface"
    """분석기. surface 는 의존성 0, kiwi 는 `pip install hanlint[kiwi]` 가 필요하다."""
    keywordField: str | None = None
    """대표 검색어를 읽을 frontmatter 필드. 없으면 keywordMissing 은 돌지 않는다."""
    introFields: list[str] = field(default_factory=list)
    """도입이 답해야 하는 frontmatter 필드 이름들. 비어 있으면 fieldEcho 는 돌지 않는다."""
    endingFields: list[str] = field(default_factory=list)
    """마지막 절이 담아야 하는 frontmatter 필드 이름들. 비어 있으면 fieldEcho 는 돌지 않는다."""
    profile: str | None = None
    """프로파일 파일 경로. 있으면 편차 구간을 notice 로 낸다."""
    baseline: str | None = None
    """잠근 지적을 적은 파일 경로. 있으면 그 안의 지적은 조용히 넘긴다."""
    dictionary: dict[str, list] = field(default_factory=dict)
    """사전에 더할 항목. 키는 사전 이름 (cliches, translationese, redundantPair, japaneseLoan)."""
    source: str | None = None
    """설정을 읽은 파일. 기본값이면 None. 설정 파일의 키가 아니라 loadConfig 가 채운다."""

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
    longSentenceMax: int = 30
    """이보다 어절이 많으면 긴 문장. 실측: 다섯 편의 최장 문장 23, 33, 23, 26, 45 가운데 30 을 넘는 둘이 목록을 문장에 넣은 것."""
    duplicateBlockRatio: float = 0.9
    """코드나 출력 블록의 줄 겹침이 이 비율 이상이면 거의 같은 블록. 실측: 004 의 출력 서른 줄 중 다른 것 한 줄."""
    firstResultMaxParagraphs: int = 4
    """첫 코드나 표나 그림 전에 둘 수 있는 산문 문단 수. 글쓰기 스킬의 도입 문단 넷과 같다."""
    sectionResultMinParagraphs: int = 3
    """이보다 문단이 많은 본문 절만 결과 (코드, 표, 파일) 를 요구한다. 짧은 절 (설치, 계정) 은 뺀다."""
    introMaxImages: int = 1
    """도입에 둘 수 있는 그림 수. 스킬: 도입은 문단 넷과 이미지 한 장을 넘지 않는다."""
    headingQuestionRatio: float = 0.5
    """H2 가운데 이 비율 넘게 물음표로 끝나면 과정이 아니라 FAQ 로 읽힌다."""
    moreLaterMaxChars: int = 150
    """마지막 절 목록 항목의 글자 상한. 실측: 다섯 편의 마지막 절 항목 24개가 17~196자였고 149자부터가
    문장 셋 이상으로 본문만큼 설명하는 것이었다."""
    tableOddCellMinRows: int = 4
    """한 칸만 딴 것을 물으려면 그 열에 몇 줄이 있어야 하는가. 셋 이하는 모양을 정할 수 없다."""

    def enabled(self, ruleName: str) -> bool:
        return ruleName not in self.disable and ruleName not in PRESETS[self.preset]

    def offRules(self) -> tuple[str, ...]:
        """지금 꺼져 있는 규칙 이름. 프리셋이 끈 것과 disable 이 끈 것을 합친다."""
        return tuple(sorted(set(PRESETS[self.preset]) | self.disable))

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
            elif key == "preset":
                if value not in PRESETS:
                    raise ValueError(f"preset 은 {', '.join(PRESET_NAMES)} 가운데 하나다: {value}")
                config.preset = value
            elif key == "dictionary":
                config.dictionary = dict(value)
            elif key != "source" and hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"모르는 설정 키: {key}. hanlint init 이 만드는 파일의 키만 쓴다")
        return config
