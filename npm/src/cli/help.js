// @ts-check
/** 첫 화면 다음에 보이는 작업 흐름 중심 도움말. */

export function rootHelp() {
  return `hanlint: 한국어 글에서 규칙으로 잡을 수 있는 잘못을 찾는다

일상 검사
  hanlint 글.md                         글을 검사한다
  hanlint fix 글.md                     안전한 고침만 적용한다
  hanlint hook                          AI가 쓰기 전에 글쓰기 지침을 넣어 주고, 저장한 마크다운을 같은 턴에 검사한다

요구사항 고정
  hanlint contract init 글.md --reader "독자" --goal "목표" --outline h2
  hanlint check contract.json 글.md --format text
  hanlint verify-patch contract.json 글.md patch.json

설정과 이해
  hanlint init                           설정 파일을 만든다
  hanlint doctor                         적용 설정과 꺼진 규칙을 본다
  hanlint rules                          규칙을 카테고리별로 본다
  hanlint explain <규칙>                 규칙의 이유와 예시를 본다
  hanlint patterns --rule <규칙>         다시 쓸 문장 틀을 본다
  hanlint spec --preset <종류> --chars 800
                                         쓰기 전에 볼 스펙을 만든다
  hanlint primer --preset <종류>         쓰기 전에 규칙의 고치는 법과 예시를 한 장으로 본다
  hanlint sheet src/ --preset screen    소스의 화면 글을 표 하나로 내보낸다. 고친 표는 sheet apply로 원본에 반영한다
  hanlint usage "단어 단어"             그 종류의 실제 글에서 단어가 쓰인 문장을 본다. 색인은 usage build가 만든다

추가 명령
  baseline, print
  Python 전용: audit, map, watch, profile, coverage, diff, learn, packet,
  guard, arena, blueprint, evidence, entailment, terms

명령마다의 옵션은 README의 명령 표에 있다. 폴더를 주면 그 아래 마크다운을 검사한다.
종료 코드: 0은 오류 없음, 1은 오류 있음, 2는 입력이나 설정 문제. 좋은 글인지는 판정하지 않는다.`;
}
