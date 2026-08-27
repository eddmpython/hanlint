# Changelog

hanlint 의 눈에 띄는 변경을 이 파일에 적는다. 형식은 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 를
따르고 버전은 [Semantic Versioning](https://semver.org/spec/v2.0.0.html) 이다. 변경은 [Unreleased] 에 쌓고
릴리즈 커밋에서 버전 절로 내린다.

## [Unreleased]

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

[Unreleased]: https://github.com/eddmpython/hanlint/compare/v0.0.2...HEAD
[0.0.2]: https://github.com/eddmpython/hanlint/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/eddmpython/hanlint/releases/tag/v0.0.1
