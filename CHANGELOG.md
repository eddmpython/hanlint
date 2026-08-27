# Changelog

hanlint 의 눈에 띄는 변경을 이 파일에 적는다. 형식은 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 를
따르고 버전은 [Semantic Versioning](https://semver.org/spec/v2.0.0.html) 이다. 변경은 [Unreleased] 에 쌓고
릴리즈 커밋에서 버전 절로 내린다.

## [Unreleased]

### Added

- **본보기.** 규칙마다 고치기 전과 후의 짝을 든다. 지적은 무엇이 틀렸는지 말하고 본보기는 무엇이
  맞는지 보인다. 사람이 읽는 꼴은 글 끝에 규칙마다 한 줄, `--format json` 은 지적마다 `exemplar`
  (`before`, `after`, `moved`), `hanlint explain` 은 전과 후를 여러 줄로 편다. 실측에서 실제 글의 지적
  104건 가운데 기계가 고쳐 주는 것이 0건이었고 지금은 104건 전부에 본보기가 붙는다
- **문형.** 빈칸이 있는 문장 틀 열 개와 `hanlint patterns [--rule <규칙>]`. 본보기가 고친 사례 하나라면
  문형은 그 사례를 다시 쓸 수 있는 틀이다. 출처는 글쓰기 스킬과 한국 글쓰기 책들 (이오덕, 이수열, 김정선,
  배상복) 이다. 틀마다 예시가 error 0 으로 통과하고 그것이 대신하는 문장이 실제로 잡히는 것을 게이트가
  매번 확인한다. 검사 끝의 다음 행동 줄이 그 규칙을 피하는 틀이 있으면 그리로 보낸다
- `keywordHeading`. 제목이 약속한 대표 검색어의 말이 절 제목 어디에도 없는 글
- `hanlint watch 글.md`. 저장할 때마다 다시 검사한다. 폴더도 받는다. 파이썬 쪽에만 있다
- `tests/_attempts/`. 게이트가 아니라 알아내는 자리다. 탐침 둘이 있다. `fixReach` 가 지적 가운데 기계가
  고쳐 주는 비율을, `koreanStyleBooks` 가 한국 글쓰기 책들이 드는 자리의 실제 빈도를 잰다
- 글쓰기 스킬이 세라고 한 자리를 집는 규칙 열. `numberOrphan` (앞에 나온 적 없는 기준값),
  `tableOddCell` (한 칸만 잣대가 다른 표), `moreLater` (본문만큼 긴 마지막 절 목록), `draftHistory`
  (글쓴이의 수정 이력과 자기 검증 기록), `enoughOnce` (`여기까지면 충분합니다` 의 두 번째),
  `blockUnread` (읽어 주지 않은 출력), `loneSubheading` (새 말이 없는 외동 소제목), `introImage`
  (도입 그림 상한), `headingQuestion` (물음표로 도배된 목차), `fieldEcho` (frontmatter 의 약속과 본문의 어긋남)
- `hanlint` 를 인자 없이 치면 나오는 첫 화면. 이 폴더의 마크다운 이름으로 만든 예시와 다음 걸음을 준다
- 파일 자리에 폴더를 받는다. 그 아래 마크다운을 이름 순으로 전부 검사한다
- 검사 끝의 다음 행동 한 줄. `--quiet` 는 뺀다
- `preset` 설정과 `hanlint init --preset blog|report|docs`. 글의 종류에 안 맞는 규칙을 이름 하나로 끈다
- `hanlint doctor`. 설정 출처, 분석기, 꺼진 규칙을 한 화면에
- `hanlint rules` 가 부류로 묶고 꺼진 규칙에 표시를 붙인다. `hanlint explain` 이 오타에 가까운 이름을
  주고 같은 부류와 끄는 법을 붙인다

### Changed

- `endingRepeat` 은 구간에 인과도 질문도 독자 호출도 없을 때만 낸다. 합니다체 글에서 어미 연속은 문체
  자체를 세는 것이었다 (발행본 다섯 편 실측 56건에서 17건)
- `headingUniform` 의 파이썬 판이 숫자로 끝나는 제목을 뺀 뒤의 수를 세도록 바뀌어 npm 판과 같은 문장을 낸다
- **`hanlint init --path` 가 `--output` 이 됐다.** `--path` 는 다른 명령에서 stdin 으로 넣은 글의 이름을
  뜻하므로 한 낱말이 두 가지를 뜻하지 않게 했다
- `--output` 을 받아 놓고 조용히 무시하던 자리를 없앴다. `rules` 는 실제로 파일에 쓰고, 뜻이 없던
  `fix` 와 `watch` 와 `doctor` 는 옵션을 뺀다
- `hanlint rules` 와 `hanlint explain` 이 `--format json` 을 받는다. 규칙과 기술서와 본보기와 틀을 한
  덩어리로 내므로 에이전트가 규칙을 훑을 수 있다

### Fixed

- `ellipsis` 가 인라인 코드 안의 점 셋을 잡던 오탐 (이슈 2). 여는 괄호와 대괄호만 예외로 두어 그 사이에
  큰따옴표가 끼면 예외가 풀렸다. 이제 지문의 인용 구간을 그대로 건너뛴다
- `deixis` 와 `danglingDeixis` 가 `종이 위의 크기` 를 지시어로 잡던 오탐 (이슈 3). 앞이 비었거나 뜻이
  분명한 조사 뒤일 때만 지시어로 본다
- `nounPile` 이 `직접 눌러 볼 수` 와 `몇 년 동안` 을 명사 다섯으로 세던 오탐 (토론 4). 의존명사와 관형사와
  부사 77개가 `data/nonNouns.txt` 에서 연속을 끊는다

## [0.0.7] - 2026-08-27

### Fixed

- 0.0.2 판의 `--version` 이 0.0.1 을 찍던 것. 버전을 손으로 적는 곳이 셋이라 하나를 빼먹을 수 있었다.
  이제 파이썬 정본 (`__version__`) 과 npm 경계 (`package.json`) 둘만 남기고 `pyproject.toml` 은 hatch 가
  정본을 읽으며, 게이트와 배포 워크플로가 일치를 강제한다. 0.0.2 는 표기만 틀렸고 검사 동작은 정상이다
- headingUniform 이 이 CHANGELOG 처럼 버전과 날짜로 끝나는 절 제목을 어미 통일로 잡던 오탐. 숫자로
  끝나는 제목은 판정에서 뺀다
- translationese 의 `로의` 항목이 `워크플로의` 처럼 로 로 끝나는 낱말의 관형격을 잡던 오탐. 받침 뒤
  꼴인 `으로의` 만 잡는다
- npm 동등성 게이트가 윈도 러너의 명령줄 한계 (32767자) 를 넘겨 터지던 것. 파일을 청크로 나눠 돌린다
- 버전 태그가 옛 커밋을 가리킨 채 나가던 실수. pre-push 훅이 태그 이름과 그 커밋의 `__version__` 을
  대조해 막는다

0.0.3 부터 0.0.6 까지는 게시 전 폐기했다. 태그가 잘못된 커밋에 찍히거나, npm 동등성 게이트가 CI 에서
터지거나, 버전 일원화 파일이 커밋에서 빠진 것으로, 매번 배포 워크플로의 대조가 게시를 막아 어느
레지스트리에도 없다.

## [0.0.2] - 2026-08-27

### Fixed

- ellipsis 가 `v0.0.1...HEAD` 같은 compare URL 의 점 셋을 말줄임표로 잡던 오탐. 영숫자에 붙은 점 셋은
  범위 표기라 제외한다. 이 CHANGELOG 의 링크 정의가 실측 사례다

## [0.0.1] - 2026-08-27

첫 공개판이다. 한국어 마크다운에서 반복되는 결함을 결정적으로 잡는 린터이자 글쓴이의 글짓기 도구다.
의존성 0 의 파이썬이 정본이고 npm 판은 같은 규칙, 같은 fixture 로 글자 단위로 같은 출력을 낸다
(testNpmParity 게이트). 점수와 등급은 내지 않는다. 세어서 확정할 수 있는 결함만 자리와 이유와 함께 짚는다.

### Added

- 규칙 42개. sentence (상투어, 번역투, 겹말, 일본어투, 지시어, 이중 피동, 관형격 연쇄, 명사 쌓기, 종결어미
  반복, 긴 문장, 어려운 말 등), paragraph (조각난 문단, 사실 나열, 화제 끊김), structure (제목 어미 통일,
  헤딩 건너뜀, 설명글 없는 절, 확인할 결과 없는 절), document (수 약속 불일치, 미회수 예고, 독자 부재),
  orthography (맞춤법 27, 띄어쓰기 12, 헷갈리는 말 12항목. 국립국어원 조항 근거), code (읽는 파일의 출처,
  설치 줄과 import 대조, 중복 블록, 첫 실행까지 거리, 플랫폼 전용 API)
- `hanlint fix`: 고친 표기가 확정된 지적을 원문에 적용하고 줄마다 보여 준다. `--dry-run` 은 보여 주기만 한다
- `hanlint audit` 와 `hanlint map --format html`: 지문 지도 (색이 구멍 종류) 와 문장 길이, 종결어미, 어휘,
  접속사 분포
- `hanlint print --layer`: 문장, 문단, 절, 글 지문을 JSON 으로
- `hanlint profile`: 승인된 글들의 문체 분포를 만들고 새 글의 편차 구간을 짚는다
- `hanlint coverage`: 사람 평가자 지적과 hanlint 지적의 자리 겹침 비율과 못 집은 유형 목록
- `hanlint diff`: 두 초안의 짜임, 리듬, 규칙별 지적 수의 변화
- 입출력: stdin (`-`, `--path`), `--format compact|json|github`, `--errors-only`, `--severity`, 설정 파일
  `hanlint.toml` 과 인라인 제어 주석. 따옴표와 백틱 안은 인용으로 보고 사전 규칙이 건너뛴다
- 표면: GitHub Action (`action.yml`), pre-commit 훅 (`.pre-commit-hooks.yaml`), VS Code 확장 (`vscode/`,
  저장 시 진단과 quick fix), AI 스킬 (`skills/use-hanlint/SKILL.md`)
- 형태소 정밀 모드 (`pip install hanlint[kiwi]`) 는 선택이고 기본은 표층 근사다

[Unreleased]: https://github.com/eddmpython/hanlint/compare/v0.0.7...HEAD
[0.0.7]: https://github.com/eddmpython/hanlint/compare/v0.0.2...v0.0.7
[0.0.2]: https://github.com/eddmpython/hanlint/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/eddmpython/hanlint/releases/tag/v0.0.1
