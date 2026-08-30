"""한 문체로 저장한 본보기와 문형을 검사한 글의 문체에 맞춘다."""

from __future__ import annotations

from ..analysis.grammar import HAPNIDA, REGISTERS, convertTemplate
from ..data import Exemplar, Pattern


def targetRegister(register: str | None) -> str:
    """섞임과 없음은 데이터 정본의 합니다체를 유지한다."""
    return register if register in REGISTERS else HAPNIDA


def exemplarInRegister(exemplar: Exemplar, register: str | None) -> Exemplar:
    target = targetRegister(register)
    before = convertTemplate(exemplar.before, target)
    after = convertTemplate(exemplar.after, target)
    if before.skipped or after.skipped:
        raise ValueError(f"{exemplar.rule} 본보기의 서술어를 못 풀었다: {before.skipped + after.skipped}")
    return Exemplar(exemplar.rule, before.text, after.text, exemplar.moved, exemplar.presets)


def patternInRegister(pattern: Pattern, register: str | None) -> Pattern:
    target = targetRegister(register)
    form = convertTemplate(pattern.form, target)
    example = convertTemplate(pattern.example, target)
    instead = convertTemplate(pattern.instead, target)
    skipped = form.skipped + example.skipped + instead.skipped
    if skipped:
        raise ValueError(f"{pattern.name} 문형의 서술어를 못 풀었다: {skipped}")
    return Pattern(
        name=pattern.name,
        form=form.text,
        when=pattern.when,
        example=example.text,
        instead=instead.text,
        avoids=pattern.avoids,
        source=pattern.source,
    )
