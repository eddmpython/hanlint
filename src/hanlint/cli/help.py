"""첫 화면 다음에 보이는 작업 흐름 중심 도움말."""

from __future__ import annotations


def rootHelp() -> str:
    """명령 개수보다 사용자가 하려는 일을 먼저 보여 준다."""
    return """hanlint: 한국어 마크다운에서 반복되는 결함과 계약 위반을 결정적으로 찾는다

일상 검사
  hanlint 글.md                         글을 검사한다
  hanlint fix 글.md                     안전한 고침만 적용한다
  hanlint watch 글.md                   저장할 때마다 다시 검사한다
  hanlint audit 글.md                   글의 구조와 분포를 함께 본다

요구사항 잠금
  hanlint contract init 글.md --reader "독자" --goal "목표" --outline h2
  hanlint check contract.json 글.md --format text
  hanlint verify-patch contract.json 글.md patch.json

설정과 이해
  hanlint init                           설정 파일을 만든다
  hanlint doctor                         적용 설정과 꺼진 규칙을 본다
  hanlint rules                          규칙을 부류별로 본다
  hanlint explain <규칙>                 규칙의 이유와 본보기를 본다
  hanlint patterns --rule <규칙>         다시 쓸 문장 틀을 본다

프로젝트와 평가
  baseline, profile, coverage, diff, learn, packet, guard, arena,
  blueprint, evidence, entailment, terms, map, print

자세한 옵션은 hanlint <명령> --help 로 본다. 폴더를 주면 그 아래 마크다운을 검사한다.
종료 코드: 0 error 없음, 1 error 있음, 2 입력이나 설정 문제. 좋은 글인지는 판정하지 않는다."""


__all__ = ["rootHelp"]
