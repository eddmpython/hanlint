"""설정과 임계 기본값의 정본.

규칙 함수는 여기서 읽지 자기 안에 숫자를 두지 않는다. 필드 이름이 곧 설정 파일의 키다.

```toml
[tool.hanlint]
preset = "blog"
disable = ["nounPile"]
keywordField = "primaryKeyword"
fragmentRun = 3

[tool.hanlint.dictionary]
cliches = ["우리의 여정"]
translationese = [{ pattern = "에 대한 이해", fix = "를 아는 것" }]
```
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..data.exemplars import Exemplar, projectExemplars
from ..data.operations import SurfaceOperation, projectOperations
from ..data.patches import Patch, projectPatches

SCREEN = ("screenNarration", "screenSentence", "screenTone", "screenWord")
"""화면의 글에서만 켜는 것. 산문의 모든 종류가 처음부터 끈다.

단추, 이름표, 상태, 빈 상태 같은 화면의 글은 낱말이고 종결어미가 보이면 문장이다. 산문에서는 `설정에서 언제든 바꿀 수
있습니다` 가 정상 문장이라 이 넷을 켜면 글마다 오탐이 난다. 실측: Taxly 의 화면 소스에서 낱말 자리의 문장 325건과 화면
해설·접객 말투 329건이 났고 산문 규칙 50개는 그 가운데 하나도 짚지 못했다 (2026-09-17). 프리셋 screen 이 이 넷을 켜고,
산문 프리셋에서 해설과 말투만 잡으려면 enforceStyle 에 screenNarration 과 screenTone 을 넣는다."""
PRESETS: dict[str, tuple[str, ...]] = {
    "blog": SCREEN,
    "report": ("noQuestion", "firstResultDistance", "introImage", "moreLater", "numberOrphan") + SCREEN,
    "docs": (
        "noQuestion",
        "firstResultDistance",
        "introImage",
        "moreLater",
        "draftHistory",
        "blockUnread",
        "numberOrphan",
        "duplicateBlock",
        "headingUniform",
    )
    + SCREEN,
}
REFERENCE = ("duplicateBlock", "headingUniform")
"""참고 문서와 자습서에서만 끄는 것. 둘 다 규칙이 온 자리는 blog 라 거기서는 켠 채 둔다.

`duplicateBlock` 은 거의 같은 블록을 두 번 읽으면 독자가 다른 한 줄을 찾느라 훑는다고 본다. 그런데
자습서는 명령 전후의 상태를 견주려고 같은 출력을 일부러 다시 두고, 참고 문서는 절마다 완결된 예제를
다시 싣는다. 낭비인지 전후 대조인지는 두 블록 사이 산문을 읽어야 갈린다. 실측: 발화 174건이
technicalDocs 155, guide 18, blog 1 이고 표본 20건이 전부 오탐이었다.
`headingUniform` 은 목차가 한 어미로 끝나면 나열로 읽힌다고 본다. 그런데 태스크 문서의 목차는
`생성하기 / 적용하기 / 검증하기 / 정리하기` 가 관례다. 그 목차가 순서 있는 과정인지 관례인지는 표층이
못 가른다. 실측: 발화 39건이 guide 22, technicalDocs 16, essay 1 이고 표본 20건 중 정탐이 하나였다
(2026-08-31)."""
ENCYCLOPEDIC = ("introLong",)
"""백과에서만 끄는 것.

`introLong` 은 도입이 문단 넷을 넘으면 미룬 배경 설명이라고 본다. 백과 표제어는 첫 절 앞의 머리말이
길게 정의와 요약을 담는 것이 관례다. 실측: 발화 75건 가운데 encyclopedia 가 39건이고 표본의 새
열 건이 암모니아, 독일의 국기, 레이디 가가처럼 전부 위키백과 머리말이었다 (2026-08-31)."""
NARRATIVE = ("factListParagraph",)
"""서사 글에서만 끄는 것. 설명글의 전제가 서사에는 성립하지 않는다.

`factListParagraph` 은 독자가 문장 사이 이유를 따라가야 한다고 본다. 장면과 사건이 진행하는 글에는
그 전제가 없다. 실측: 기준 말뭉치 표본에서 essay 11건이 전부 오탐이고 비-essay 9건이 전부 정탐이라
교차표에 예외가 하나도 없었다. 끄고 다시 재니 표본이 전부 비-서사로 바뀌어 기본 판정이 정탐이 됐다
(2026-08-31)."""
CONVERSATION = (
    "countMismatch",
    "duplicateBlock",
    "factListParagraph",
    "firstResultDistance",
    "headingSentence",
    "headingSkip",
    "headingUniform",
    "inputFileSource",
    "installImport",
    "introLong",
    "keywordMissing",
    "noQuestion",
    "outsideProfile",
    "paraFragment",
    "platformApi",
    "promiseRecall",
    "sectionNoProse",
)
"""대화 답변에서 끄는 것. 글의 짜임을 재는 규칙 (도입, 제목, 절, 문단 나누기, 사실 나열, 코드 블록 대조, 두 자리 대조)
은 글 한 편을 전제하고 답변 하나에는 그 전제가 없다.

목록은 cinch 의 replyHanlint 훅이 실제 답변에 맞춰 고른 것을 옮겨 왔다. 실측 (2026-08-28): 답변 8건에 문장 규칙만
남기니 2건이 걸렸고 둘 다 운영자가 따로 읽기 힘들다고 한 문장이었다. countMismatch 는 답변 하나에 서로 다른
나열이 여럿이라 단위를 한 약속으로 읽어 끈다. 견줄 답변 말뭉치가 없어 프로파일은 없고, 그래서 어차피 침묵하는
outsideProfile 도 끈 것으로 적는다. 켜진 것처럼 보이는 규칙이 잡히지 않는 것보다 정직하다."""
PRESETS["guide"] = PRESETS["blog"] + REFERENCE
PRESETS["essay"] = PRESETS["report"] + NARRATIVE
PRESETS["fiction"] = PRESETS["report"] + NARRATIVE
PRESETS["encyclopedia"] = PRESETS["docs"] + ENCYCLOPEDIC
PRESETS["chat"] = CONVERSATION + SCREEN
SCREEN_OFF = (
    "cliche",
    "connectorRepeat",
    "danglingDeixis",
    "deixis",
    "doubleNegative",
    "draftHistory",
    "endingRepeat",
    "euiChain",
    "fillerOpener",
    "imperativePeriod",
    "longSentence",
    "negationRedefine",
    "nounPile",
    "numberOrphan",
    "outsideProfile",
    "factListParagraph",
    "paraFragment",
    "blockUnread",
    "bridgeRepeat",
    "emojiBullet",
    "headingSentence",
    "headingSkip",
    "headingUniform",
    "introImage",
    "introLong",
    "loneSubheading",
    "moreLater",
    "sectionNoProse",
    "countMismatch",
    "enoughOnce",
    "fieldEcho",
    "keywordHeading",
    "keywordMissing",
    "noQuestion",
    "promiseRecall",
    "tableOddCell",
    "duplicateBlock",
    "firstResultDistance",
    "inputFileSource",
    "installImport",
    "platformApi",
)
"""화면의 글에서 끄는 것. 문장과 문단과 글의 짜임을 재는 규칙은 화면의 글 한 마디에 전제가 없다.

남는 것은 SCREEN 셋과 낱말 안에서 결정되는 것 (dash, spelling, spacing, confusable, hardWord, japaneseLoan,
doublePassive, translationese, redundantPair) 이다. nounPile 은 끈다. `수임처 자료 수집 실패` 처럼 화면의 낱말은 명사가
이어지는 것이 정상이다. imperativePeriod 와 cliche 와 doubleNegative 는 문장을 전제하므로 끈다. 종결어미 자체를
screenSentence 가 잡는다 (2026-09-17)."""
PRESETS["screen"] = SCREEN_OFF
"""글의 종류마다 처음부터 끄고 시작할 규칙. `preset` 키가 고르고 `disable` 이 그 위에 더한다.

blog 는 화면 규칙 셋만 끄고 전부 켠다. 독자를 부르고 절마다 결과를 남기는 글이 기준이다.
screen 은 화면의 글이다. 낱말 안에서 결정되는 규칙과 화면 규칙 셋만 남긴다.
report 는 보고서다. 독자에게 말을 걸지 않고 절이 결과를 남기지 않으며 도입이 짧을 필요가 없다.
docs 는 참고 문서와 명세다. report 에 더해 검증 사실을 남기는 것 (draftHistory) 과 그림을 text 펜스로
그리는 것 (blockUnread) 이 제 일이다. 실측: 이 저장소의 hanlint.toml 이 noQuestion 과 readerAbsent 를
손으로 끄고 있었다. 프리셋은 그 손질을 이름 하나로 바꾼 것이다.
나머지 넷은 위의 셋에 종류가 요구하는 것을 더한다. guide (단계별 안내) 는 blog 에 REFERENCE 를,
essay 와 fiction (1930년대 문학) 은 report 에 NARRATIVE 를, encyclopedia (백과) 는 docs 에
ENCYCLOPEDIC 을 더한다. 그래도 종류가 다른 것은 견주는 프로파일 (PROFILE_OF) 이다.
numberOrphan 은 실행 결과가 있는 글 (blog, guide) 에만 켠다. 실측: 백과와 뉴스의 표본 19건이 전부 서술의 A에서 B로 였다
(2026-08-29). 그 글에는 앞서 보인 실행이 없으니 기준값이 앞에 나올 이유도 없다.
"""

PROFILE_OF = {
    "blog": "blog",
    "report": "report",
    "docs": "technicalDocs",
    "guide": "guide",
    "essay": "essay",
    "fiction": "fiction",
    "encyclopedia": "encyclopedia",
    "chat": None,
    "screen": None,
}
"""프리셋 → 견줄 프로파일의 종류. data/profiles.json 의 키이고 정본은 corpus/catalogue.toml 의 types 다. 규칙
outsideProfile 이 읽는다. chat 과 screen 은 견줄 말뭉치가 없어 None 이고 그 종류는 견주지 않는다."""

USAGE_OF = {"report": "report"}
"""프리셋 → 용례 빈도표의 종류 (data/usageCounts.<종류>.json). 없는 프리셋은 용례를 보지 않는다. 사업보고서에서 센
빈도표는 보고서의 관용 연쇄이지 블로그와 안내의 관용이 아니다. 설정 usageKind 가 이 기본을 덮는다."""
USAGE_KINDS = tuple(sorted(set(USAGE_OF.values())))
"""실린 빈도표의 종류. scripts/derive/usageCounts.py 가 만들고 tests/gates/testUsageCounts.py 가 크기와 꼴을 지킨다."""

PRESET_NAMES = tuple(PRESETS)
DEFAULT_PRESET = PRESET_NAMES[0]
ENFORCEABLE = ("noQuestion", "nounPile", "screenNarration", "screenTone", "screenWord")
"""enforceStyle 에 넣을 수 있는 규칙. 프리셋이 꺼도 사용자가 오류로 되살리는 것들이다."""
"""설정도 옵션도 없을 때의 종류. 이 이름일 때는 출력에 프리셋을 적지 않는다."""


def shown(value: object) -> str:
    """오류 문구에 적는 설정 값. JSON 꼴이라 npm 판 (JSON.stringify) 과 글자가 같다. 검증에서 true 와 True 가 갈렸다."""
    return json.dumps(value, ensure_ascii=False, default=str)


@dataclass
class Config:
    preset: str = PRESET_NAMES[0]
    """글의 종류. PRESETS 가 정한 규칙을 처음부터 끈다. disable 은 그 위에 더한다."""
    disable: set[str] = field(default_factory=set)
    """끌 규칙 이름."""
    keywordField: str | None = None
    """대표 검색어를 읽을 frontmatter 필드. 없으면 keywordMissing 은 돌지 않는다."""
    introFields: list[str] = field(default_factory=list)
    """도입이 답해야 하는 frontmatter 필드 이름들. 비어 있으면 fieldEcho 는 돌지 않는다."""
    endingFields: list[str] = field(default_factory=list)
    """마지막 절이 담아야 하는 frontmatter 필드 이름들. 비어 있으면 fieldEcho 는 돌지 않는다."""
    profile: str | None = None
    """사용자 프로파일 파일 경로 (hanlint profile build 가 만든 것). 있으면 종류의 프로파일 대신 그것과 견준다."""
    profilePercentile: int = 99
    """outsideProfile 이 짚는 백분위. 프로파일에 있는 50, 90, 95, 99 가운데 하나다."""
    countMismatchSpan: int = 60
    """절이 없는 글이 이 줄 수 안일 때만 countMismatch 가 글 전체를 견준다. 절이 있으면 도입과 마지막 절만 견준다."""
    baseline: str | None = None
    """잠근 지적을 적은 파일 경로. 있으면 그 안의 지적은 조용히 넘긴다."""
    dictionary: dict[str, list] = field(default_factory=dict)
    """사전에 더할 항목. 키는 사전 이름 (cliches, translationese, redundantPair, japaneseLoan)."""
    exemplars: tuple[Exemplar, ...] = ()
    """사람이 승인해 `[[exemplars]]` 로 넣은 프로젝트 본보기."""
    patches: tuple[Patch, ...] = ()
    """사람이 승인해 `[[patches]]` 로 넣은 국소 고침. 원문을 포함한 모든 조건이 맞을 때만 재생한다."""
    operations: tuple[SurfaceOperation, ...] = ()
    """사람이 승인한 32자 이하 표면 치환. 단어 경계와 보호 원자가 맞는 다른 원문 한 자리에도 쓴다."""
    protectedTerms: list[str] = field(default_factory=list)
    """표면 치환이 바꾸면 안 되는 한국어 고유명사와 프로젝트 용어. 라틴 식별자와 수치는 자동으로 보호한다."""
    ignoreFences: list[str] = field(default_factory=list)
    """지문에서 뺄 펜스의 언어 표기. 코드도 산문도 아닌 펜스 (강의 장면 계약, 도표 원문) 가 코드 블록으로 세어지면
    거의 같은 블록, 읽어 주지 않은 출력, 절의 결과로 잘못 잡힌다. 실측: eddmpython-course 의 `course-scene` 펜스가
    여섯 편에서 duplicateBlock 21건과 blockUnread 1건을 냈다. 렌더러가 읽기 본문에서 지우는 펜스는 지문에서도 뺀다."""
    source: str | None = None
    """설정을 읽은 파일. 기본값이면 None. 설정 파일의 키가 아니라 loadConfig 가 채운다."""

    fragmentRun: int = 3
    """한두 문장짜리 문단이 몇 개 이어지면 조각남으로 보는가."""
    introMaxParagraphs: int = 4
    """도입 산문 문단 상한. 스킬: 도입은 문단 넷을 넘지 않는다."""
    headingUniformRatio: float = 0.75
    """H2 끝 글자가 이 비율 넘게 같으면 통일로 본다. 실측: 004 는 8 중 7 이라 0.875 였다."""
    headingSentenceMaxLevel: int = 6
    """문장형 제목을 잡을 제목 깊이의 상한. 기본은 전부 (H1~H6). 절 제목 아래에 문장형 부제를 두는 형식 (강의 교안의
    H3 부제) 은 2 로 두어 H2 까지만 본다. 실측: eddmpython-course 는 H3 부제가 계약상 문장이라 여섯 편에서 62건이 났다."""
    bridgeRepeatMin: int = 3
    """절을 닫는 문장이 같은 이음 표지 (이번에는, 이제, 다음으로) 로 시작하는 절이 몇 개면 틀로 보는가. 실측:
    eddmpython-course 03 은 14절 가운데 12절이 `이번에는` 으로 닫혔고 기준 말뭉치 390편에서 문장 첫머리
    `이번에는` 은 1건이었다. 둘은 우연이고 셋부터 틀이다."""
    nounPileMin: int = 5
    """명사가 몇 개 이어지면 나열로 보는가. 넷은 `파이썬 데이터프레임 라이브러리` 같은 정상 표현이라 다섯부터."""
    usageKind: str | None = None
    """용례 빈도표의 종류. None 이면 프리셋이 정한다 (USAGE_OF). "" 는 어떤 프리셋에서도 용례를 보지 않는다."""
    usageShare: float = 0.9
    """사전 항목 (번역투, 어려운 말, 상투어) 이 그 종류의 문서 몇 할에 나오면 관용으로 보고 짚지 않는가. 실측: 사업보고서
    200편에서 translationese 항목 8개 (`에 대한`, `을 통해`, `로부터`, `에 관한`, `로 인해`, `을 위해`, `에 대해`,
    `에 의해`) 와 `상기`, `를 가지고 있` 이 문서의 95~100% 에 나왔고 다음 항목 (`에 있어서`) 은 70% 였다. 0.9 가 그 틈을
    가른다. 열 편 가운데 아홉 편이 쓰는 표현은 그 종류의 말이다 (2026-09-19)."""
    usageMin: int = 3
    """명사 연쇄가 몇 편의 문서에 나와야 그 종류의 용례로 보는가. 둘은 우연이고 셋부터 관용이다 (bridgeRepeatMin 과
    같은 셈). 실측: 사업보고서 961편에서 nounPile 이 짚은 연쇄 5,011건 가운데 다른 문서 2편 이상에 나온 것이 22.4%,
    3편 이상이 21.0%, 10편 이상이 18.7% 였다. 둘과 셋의 차이는 작고 셋이 우연을 거른다 (2026-09-19). 표 자체가 셋 이상의
    연쇄만 들므로 (scripts/derive/usageCounts.py) 이 값을 셋 아래로 내려도 셋과 같다."""
    endingRun: int = 4
    """같은 종결어미가 몇 문장 이어지면 반복으로 보는가. im-not-ai E-2 의 4 를 출발점으로."""
    factListMinSentences: int = 3
    """인과 표지 없는 문단을 사실 나열로 보는 최소 문장 수."""
    factListMaxMeanLength: float = 8.0
    """사실 나열로 볼 문단의 평균 어절 수 상한. 긴 문장은 안에서 이미 이어져 있다. 실측: 004 의 오탐 문단은 평균 9~15 어절."""
    flowValleyMinSentences: int = 2
    """`hanlint audit` 의 흐름 골짜기로 볼 때 앞뒤 문단의 최소 문장 수. 한 문장 문단은 중첩이 원래 작다.

    2026-08-31 까지는 규칙 topicBreak 의 임계였다. 그 규칙을 빼면서 이름을 지금 쓰는 곳에 맞췄다.
    골짜기는 지도가 보이는 사실이고 결함 판정이 아니다."""
    longSentenceMax: int = 30
    """이보다 어절이 많으면 긴 문장. 실측: 다섯 편의 최장 문장 23, 33, 23, 26, 45 가운데 30 을 넘는 둘이 목록을 문장에 넣은 것."""
    duplicateBlockRatio: float = 0.9
    """코드나 출력 블록의 줄 겹침이 이 비율 이상이면 거의 같은 블록. 실측: 004 의 출력 서른 줄 중 다른 것 한 줄."""
    firstResultMaxParagraphs: int = 4
    """첫 코드나 표나 그림 전에 둘 수 있는 산문 문단 수. 글쓰기 스킬의 도입 문단 넷과 같다."""
    introMaxImages: int = 1
    """도입에 둘 수 있는 그림 수. 스킬: 도입은 문단 넷과 이미지 한 장을 넘지 않는다."""
    moreLaterMaxChars: int = 150
    """마지막 절 목록 항목의 글자 상한. 실측: 다섯 편의 마지막 절 항목 24개가 17~196자였고 149자부터가
    문장 셋 이상으로 본문만큼 설명하는 것이었다."""
    tableOddCellMinRows: int = 4
    """한 칸만 딴 것을 물으려면 그 열에 몇 줄이 있어야 하는가. 셋 이하는 모양을 정할 수 없다."""
    registerMinShare: float = 0.7
    """평서문 가운데 가장 많은 문체가 이 비율 아래면 섞임으로 본다. 기준 말뭉치 390편에서 안내와 기술
    문서의 최솟값은 0.9778, 에세이 하위 5%는 0.7576이었고 실제 혼합 기사 한 편은 0.625였다. 0.7은
    그 기사를 섞임으로 가르면서 일관된 발행문을 보존한다 (2026-08-28)."""

    enforceStyle: list[str] = field(default_factory=list)
    """사용자가 오류로 강제할 문체 신호. 기본은 참고 지적이다. 산문 프리셋에서 화면 해설 (screenNarration) 과 접객 말투
    (screenTone) 를 잡으려면 여기에 넣는다. 문장이 허용된 화면 글 (장표, 고지) 을 chat 으로 재는 자리다."""

    def __post_init__(self) -> None:
        if not isinstance(self.enforceStyle, list) or any(name not in ENFORCEABLE for name in self.enforceStyle):
            raise ValueError(f"enforceStyle 은 {', '.join(ENFORCEABLE)}의 배열이다")
        if self.usageKind is not None and self.usageKind != "" and self.usageKind not in USAGE_KINDS:
            raise ValueError(f"usageKind 는 {', '.join(USAGE_KINDS)} 가운데 하나이거나 빈 문자열이다: {shown(self.usageKind)}")
        if not isinstance(self.protectedTerms, list) or not all(
            isinstance(item, str) and item.strip() for item in self.protectedTerms
        ):
            raise ValueError(f"protectedTerms 는 비지 않은 문자열의 배열이다: {shown(self.protectedTerms)}")
        self.protectedTerms = [item.strip() for item in self.protectedTerms]
        if self.exemplars:
            if all(isinstance(exemplar, Exemplar) for exemplar in self.exemplars):
                self.exemplars = tuple(self.exemplars)
            else:
                self.exemplars = projectExemplars(self.exemplars, PRESET_NAMES)
        if self.patches:
            if all(isinstance(patch, Patch) for patch in self.patches):
                self.patches = tuple(self.patches)
            else:
                self.patches = projectPatches(self.patches, PRESET_NAMES)
        if self.operations:
            if all(isinstance(operation, SurfaceOperation) for operation in self.operations):
                self.operations = tuple(self.operations)
            else:
                self.operations = projectOperations(self.operations, PRESET_NAMES)

    def enabled(self, ruleName: str) -> bool:
        return ruleName not in self.disable and (ruleName not in PRESETS[self.preset] or ruleName in self.enforceStyle)

    def offRules(self) -> tuple[str, ...]:
        """지금 꺼져 있는 규칙 이름. 프리셋이 끈 것과 disable 이 끈 것을 합친다."""
        return tuple(sorted((set(PRESETS[self.preset]) - set(self.enforceStyle)) | self.disable))

    @classmethod
    def fromMapping(cls, data: dict) -> Config:
        config = cls()
        for key, value in data.items():
            if key == "disable":
                config.disable = set(value)
            elif key == "analyzer":
                # 0.0.7 까지의 키. hanlint init 이 surface 를 써 넣었으므로 그 값은 조용히 넘기고 다른 값은 빠졌다고 알린다.
                if value != "surface":
                    raise ValueError(f"analyzer 설정은 빠졌다. 분석기는 표층 하나라 키를 지운다: {shown(value)}")
            elif key == "preset":
                if value not in PRESETS:
                    raise ValueError(f"preset 은 {', '.join(PRESET_NAMES)} 가운데 하나다: {shown(value)}")
                config.preset = value
            elif key == "enforceStyle":
                config.enforceStyle = cls(enforceStyle=value).enforceStyle
            elif key == "dictionary":
                config.dictionary = dict(value)
            elif key == "exemplars":
                config.exemplars = projectExemplars(value, PRESET_NAMES)
            elif key == "patches":
                config.patches = projectPatches(value, PRESET_NAMES)
            elif key == "operations":
                config.operations = projectOperations(value, PRESET_NAMES)
            elif key in ("ignoreFences", "introFields", "endingFields", "protectedTerms"):
                if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                    raise ValueError(f"{key} 는 문자열 배열이다: {shown(value)}")
                names = [item.strip() for item in value]
                setattr(config, key, [name.lower() for name in names] if key == "ignoreFences" else names)
            elif key != "source" and hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"모르는 설정 키: {key}. hanlint init 이 만드는 파일의 키만 쓴다")
        return config
