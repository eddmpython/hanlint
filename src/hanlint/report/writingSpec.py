"""쓰기 전 숫자 사양. 배포 프로파일의 관찰값 위에 현재 설정에서 켜진 규칙의 요구를 얹는다.

리듬 악보 3회차의 초안 열두 편에서 어절 하나가 공백을 포함해 4.6자에서 7.1자였다. 분량 역산에는 그
가운데 6자를 쓴다. 이 값은 검사 임계가 아니라 목표 분량을 문장 수로 바꾸는 근삿값이다. 나머지 수는
모두 배포 프로파일이나 Config에서 매번 읽는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

from ..analysis.grammar import HAPNIDA, REGISTERS
from ..config.settings import PROFILE_OF, Config
from ..data.profiles import Profile, profileOf, userProfile

SPEC_VERSION = 1
CHARS_PER_WORD = 6


@dataclass(frozen=True)
class WritingSpecRow:
    """사양 한 줄. basis는 그 줄을 다시 계산할 정본이다."""

    id: str
    label: str
    guidance: str
    basis: tuple[str, ...]

    def asDict(self) -> dict:
        return {"id": self.id, "label": self.label, "guidance": self.guidance, "basis": list(self.basis)}


@dataclass(frozen=True)
class WritingSpec:
    """프로파일과 규칙판을 쓰기 전에 읽을 숫자로 편 결과."""

    preset: str
    register: str
    targetChars: int | None
    profile: str
    rows: tuple[WritingSpecRow, ...]

    def asDict(self) -> dict:
        return {
            "version": SPEC_VERSION,
            "kind": "hanlint.writingSpec",
            "preset": self.preset,
            "register": self.register,
            "targetChars": self.targetChars,
            "profile": self.profile,
            "rows": [row.asDict() for row in self.rows],
        }


def nearest(value: float) -> int:
    """양수 반올림. Python의 bankers rounding과 JavaScript의 차이를 만들지 않는다."""
    return floor(value + 0.5)


def percentile(histogram, level: int) -> int:
    return histogram.percentile(level)


def percent(value: float) -> int:
    return nearest(value * 100)


def selectedProfile(config: Config) -> Profile:
    if config.profile:
        return userProfile(config.profile)
    kind = PROFILE_OF[config.preset]
    if kind is None:
        raise ValueError(f"{config.preset} 은 종류 프로파일이 없어 사양을 낼 수 없다")
    profile = profileOf(kind)
    if profile is None:
        raise ValueError(f"{kind} 프로파일을 찾지 못했다")
    return profile


def writingSpec(
    config: Config | None = None,
    register: str = HAPNIDA,
    targetChars: int | None = None,
) -> WritingSpec:
    """현재 규칙판을 쓰기 전 숫자 사양으로 편다. 품질 점수나 새 임계는 만들지 않는다."""
    config = config or Config()
    if register not in REGISTERS:
        raise ValueError(f"register 는 {', '.join(REGISTERS)} 가운데 하나다: {register}")
    if targetChars is not None and targetChars <= 0:
        raise ValueError(f"chars 는 1 이상이어야 한다: {targetChars}")
    profile = selectedProfile(config)
    sentence = profile.sentence
    paragraph = profile.paragraph["sentenceCount"]
    perParagraph = percentile(paragraph, 50)
    if perParagraph <= 0:
        raise ValueError("프로파일의 문단당 문장 중앙값이 1 이상이어야 한다")
    lengthP50 = percentile(sentence["length"], 50)
    if lengthP50 <= 0:
        raise ValueError("프로파일의 문장 길이 중앙값이 1 이상이어야 한다")

    rows: list[WritingSpecRow] = []
    amount = f"문단마다 문장 {perParagraph}~{percentile(paragraph, 90)}개"
    if targetChars is not None:
        sentences = max(1, nearest(targetChars / CHARS_PER_WORD / lengthP50))
        paragraphs = max(1, nearest(sentences / perParagraph))
        amount = f"문단 {paragraphs}개, {amount}, 문장 {sentences}개 안팎"
    rows.append(WritingSpecRow("amount", "분량", amount, (f"profile.{profile.kind}.paragraph.sentenceCount",)))

    length = f"중앙 {lengthP50}어절, 문장 90%가 {percentile(sentence['length'], 90)}어절 이하"
    lengthBasis = [f"profile.{profile.kind}.sentence.length"]
    if config.enabled("longSentence"):
        length += f". {config.longSentenceMax}어절을 넘으면 longSentence가 지적"
        lengthBasis.append("rule.longSentence")
    rows.append(WritingSpecRow("sentenceLength", "문장 길이", length, tuple(lengthBasis)))

    ending = profile.endingRuns
    if ending is not None:
        endingText = f"같은 끝맺음 연속 중앙 {percentile(ending, 50)}개, 90%가 {percentile(ending, 90)}개 이하"
        endingBasis = [f"profile.{profile.kind}.endingRuns"]
        if config.enabled("endingRepeat"):
            endingText += f". 인과나 독자 호출 없이 {config.endingRun}개부터 endingRepeat가 지적"
            endingBasis.append("rule.endingRepeat")
        rows.append(WritingSpecRow("endingRun", "끝맺음", endingText, tuple(endingBasis)))

    commas = sentence["commas"]
    rows.append(
        WritingSpecRow(
            "commas",
            "쉼표",
            f"문장 중앙 {percentile(commas, 50)}개, 90%가 {percentile(commas, 90)}개 이하, 99%가 {percentile(commas, 99)}개 이하",
            (f"profile.{profile.kind}.sentence.commas",),
        )
    )

    eui = sentence["euiCount"]
    euiText = f"문장 중앙 {percentile(eui, 50)}개, 90%가 {percentile(eui, 90)}개 이하"
    euiBasis = [f"profile.{profile.kind}.sentence.euiCount"]
    if config.enabled("euiChain"):
        euiText += ". 3개부터, 붙은 2개부터 euiChain이 지적"
        euiBasis.append("rule.euiChain")
    rows.append(WritingSpecRow("euiCount", "의", euiText, tuple(euiBasis)))

    nounRun = sentence["nounRun"]
    nounText = f"문장 90%에서 조사 없는 명사 연쇄가 {percentile(nounRun, 90)}개 이하"
    nounBasis = [f"profile.{profile.kind}.sentence.nounRun"]
    if config.enabled("nounPile"):
        nounText += f". {config.nounPileMin}개부터 nounPile이 지적"
        nounBasis.append("rule.nounPile")
    rows.append(WritingSpecRow("nounRun", "명사 연쇄", nounText, tuple(nounBasis)))

    newTopics = sentence["newTopics"]
    rows.append(
        WritingSpecRow(
            "newTopics",
            "새 화제",
            f"문장 중앙 {percentile(newTopics, 50)}개, 90%가 {percentile(newTopics, 90)}개 이하",
            (f"profile.{profile.kind}.sentence.newTopics",),
        )
    )

    connector = profile.rates["connector"]
    rows.append(
        WritingSpecRow(
            "connector",
            "문두 접속",
            f"문서 중앙은 문장의 {percent(connector['p50'])}%, 문서 90%가 {percent(connector['p90'])}% 이하",
            (f"profile.{profile.kind}.rates.connector",),
        )
    )

    numbers = sentence["numbers"]
    numberP50 = percentile(numbers, 50)
    numberP90 = percentile(numbers, 90)
    numberText = (
        "문장 중앙과 90%에서 숫자 없음" if numberP50 == numberP90 == 0 else f"문장 중앙 {numberP50}개, 90%가 {numberP90}개 이하"
    )
    rows.append(WritingSpecRow("numbers", "숫자", numberText, (f"profile.{profile.kind}.sentence.numbers",)))

    question = profile.rates["question"]
    if config.enabled("noQuestion"):
        questionText = (
            "선택한 정책: 절이 2개 이상이면 글 전체에 물음표 최소 1개"
            if "noQuestion" in config.enforceStyle
            else "물음표 부재는 notice다. 질문 없이 충분히 설명했다면 유지한다"
        )
        questionBasis = (f"profile.{profile.kind}.rates.question", "rule.noQuestion")
    else:
        questionText = (
            f"규칙 요구 없음. 문서 중앙은 문장의 {percent(question['p50'])}%, 문서 90%가 {percent(question['p90'])}% 이하"
        )
        questionBasis = (f"profile.{profile.kind}.rates.question",)
    rows.append(WritingSpecRow("question", "물음표", questionText, questionBasis))

    return WritingSpec(config.preset, register, targetChars, profile.kind, tuple(rows))


def renderWritingSpec(spec: WritingSpec) -> str:
    """사람이 읽는 꼴. basis는 JSON에서 확인한다."""
    target = f", {spec.targetChars}자" if spec.targetChars is not None else ""
    lines = [
        f"hanlint spec  {spec.preset} 종류, {spec.register}체{target}. "
        f"같은 규칙판의 임계와 {spec.profile} 프로파일을 쓰기 전 숫자로 편다"
    ]
    width = max(len(row.label) for row in spec.rows)
    lines.extend(f"  {row.label:<{width}}  {row.guidance}" for row in spec.rows)
    lines.extend(
        (
            "",
            "이 사양은 품질 점수가 아니다. 쓴 뒤 같은 설정으로 hanlint <글.md>를 실행해 Finding을 확인한다",
        )
    )
    return "\n".join(lines)


__all__ = ["SPEC_VERSION", "WritingSpec", "WritingSpecRow", "renderWritingSpec", "writingSpec"]
