---
id: start.cli
title: 명령과 설정
category: start
purpose: 파일 검사, 설정, 기존 문서 도입과 명령 선택을 안내한다. 옵션의 정본은 실행한 배포판의 도움말이다.
whenToUse:
  - 터미널에서 검사하고 고친다
  - 프리셋과 baseline을 설정한다
  - Python과 npm의 명령 범위를 확인한다
status: curated
---

# 명령과 설정

[처음으로](../../../README.md) · [자동화 연결](integrations.md) · [브라우저 편집기](https://eddmpython.github.io/hanlint/)

Python은 `pip install hanlint`로 설치하고, Node는 `npx hanlint`로 실행한다.
아래 공통 명령의 `hanlint`를 `npx hanlint`로 바꿔도 된다. 설치 요구사항과 공개 API는
[README](../../../README.md)와 [npm 안내](../../../npm/README.md)를 따른다.

## 읽고, 고치고, 다시 검사하기

```console
hanlint 글.md
hanlint fix 글.md
hanlint 글.md
```

첫 명령은 글을 읽기만 한다. `fix`는 확정할 수 있는 고침을 파일에 적용한다. 자동으로 고친 뒤에도 남은
지적과 뜻을 읽는다. 본보기와 후보는 문장을 다시 쓰는 데 참고할 자료이며 자동 적용 결과와 구분한다.

```console
hanlint explain doublePassive
hanlint patterns --rule nounPile
```

한 번에 여러 파일이나 폴더를 줄 수 있다. 폴더는 하위 마크다운을 포함한다. stdin으로 넣을 때는
`--path`에 원고 이름을 주면 결과에서 그 이름을 사용한다.

```console
hanlint 소개.md 사용법.md
hanlint 문서들/ --preset docs
hanlint - --path 초안.md
```

## 실제 지적 읽기

프로젝트 설정이 없는 폴더에서 기본 blog 프리셋으로 다음 글을 검사한다.

```markdown
결과가 저장되어집니다.

가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
```

```text
설정: 기본값, 프리셋 blog

글.md  집은 자리 1, 확인할 자리 1

글.md:1  [doublePassive]
  결과가 저장되어집니다.
  `되어지` 는 피동에 어지다 를 또 붙인 이중 피동이다. 하나만 남긴다
  고친 뒤: 결과가 저장됩니다.

글.md:3  [nounPile] 확인
  가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
  명사 6개가 조사 없이 이어진다. 관계가 표시되지 않아 독자가 조사를 끼워 넣는다. 동사로 되돌린다

본보기 (고치기 전, 고친 뒤)
  [doublePassive]
    전  결과가 저장되어집니다.
    후  결과가 저장됩니다.
  [nounPile]
    전  가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
    후  가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다.

다음: error 1건 가운데 1건은 hanlint fix 가 바로 고친다. 나머지는 손으로 고친다
```

위치와 규칙, 이유와 고친 표기를 함께 읽는다. error는 고칠 결함이고 notice는 문맥에 따라 판단할 자리다.
이 출력은 같은 글을 실제로 검사한 결과와 대조하는 게이트로 유지한다.

## 화면의 글을 표 하나로 보기

앱의 화면 글 (단추, 이름표, 상태, 안내) 은 수십 소스 파일에 흩어져 있어 파일마다 지적을 받으면 전체가 안 보인다.
`sheet` 는 소스 파일 (js, jsx, mjs, cjs, ts, tsx, rs, py, html, htm, vue, svelte) 을 전부 뒤져 한국어 문자열과
태그 사이 글, 속성값을 표 하나로 떨군다. 같은 줄에서 인라인 태그 (`<strong>`, `<a>`) 만 사이에 둔 글은 한 마디로 잇고
(원문은 태그째, 검사는 태그 없이), 마크업 파일의 여러 줄 문단은 줄마다 한 마디다. `<script>` 안은 코드라 따옴표 글만 본다.

```console
hanlint sheet src/ --preset screen --output 시트.md
hanlint sheet src/ --preset screen --all --format json
hanlint sheet apply 시트.md --dry-run
hanlint sheet apply 시트.md
```

표의 칸은 번호, 자리 (`경로:줄:칸`), 글, 지적, 고침이다. 사람이 `고침` 칸에 새 글을 적고 `apply` 를 돌리면 그 줄의 그 칸에
있는 글을 새 글로 바꿔 쓴다. 칸이 없는 자리 (`경로:줄`) 는 그 줄에서 글이 정확히 한 번 있을 때만 바꾸고, 없거나 두 번이면
실패로 적는다. 표를 뽑은 뒤 파일이 바뀌어 칸이 어긋나면 표를 다시 뽑는다. 글을 지우거나 요소를 없애는
일은 코드를 열어 손으로 한다. 주석과 개발자용 줄 (`new Error(`, `console.`, `assert`) 은 표에 안 나온다.

설치 없이 보려면 [브라우저 편집기](https://eddmpython.github.io/hanlint/) 의 원문 칸에 공개 GitHub 저장소 주소를 붙여
넣는다. 같은 표가 뜨고 내려받은 시트를 `hanlint sheet apply` 가 그대로 읽는다.

## 프리셋과 설정

글의 목적이 달라지면 프리셋부터 고른다. `blog`, `docs`, `report`, `guide`, `essay`, `fiction`,
`encyclopedia`, `chat`, `screen`을 지원한다. `chat`은 대화 답변용이며 문서의 짜임을 재는 규칙을 줄인다. `screen`은
화면의 글 (단추, 이름표, 상태, 빈 상태) 용이며 낱말 자리의 문장, 화면 해설, 접객 말투, 개발 어휘를 잡고 산문 규칙은
끈다. 프로젝트가 한 이름으로 정한 낱말 (데이터 → 자료) 은 설정의 `dictionary.screenWord` 에 적는다. 산문 프리셋에서
화면 해설과 접객 말투와 낱말만 잡으려면 `enforceStyle = ["screenNarration", "screenTone", "screenWord"]` 을 둔다.

| 프리셋 | 글의 목적 | 끄는 규칙 | 견주는 프로파일 |
|---|---|---:|---|
| `blog` | 독자를 부르고 절마다 결과를 남기는 글 | 4개 | 블로그 |
| `guide` | 단계별 안내서 | 6개 | 안내서 |
| `report` | 보고서 | 9개 | 보고문 |
| `essay` | 수필 | 10개 | 수필 |
| `fiction` | 소설 | 10개 | 소설 |
| `docs` | 참고 문서, 명세, README | 13개 | 기술 문서 |
| `encyclopedia` | 백과 항목 | 14개 | 백과 |
| `chat` | 대화 답변. 글의 짜임을 재는 규칙을 끈다 | 21개 | 없음 |
| `screen` | 화면의 글. 낱말 안에서 결정되는 규칙과 화면 규칙만 남긴다 | 41개 | 없음 |

표의 행과 수는 설정 코드와 자동 대조한다. 기본값과 꺼지는 규칙은 [설정 코드](../../../src/hanlint/config/settings.py)와 실행 결과에서 확인한다.

```console
hanlint 글.md --preset report
hanlint init --preset docs
hanlint doctor
hanlint rules --preset docs
```

`--preset`은 이번 실행에만 적용한다. `init`은 주석이 붙은 `hanlint.toml`을 만든다. 이미 설정이 있으면
필요한 항목을 편집한다. `doctor`로 실제로 읽은 설정과 프리셋, 꺼진 규칙, baseline을 확인한다.

한 문단의 인용처럼 문맥상 예외인 곳에는 마크다운 주석을 사용할 수 있다.

```markdown
<!-- hanlint-disable cliche -->

예외로 둘 인용 문단

<!-- hanlint-enable cliche -->
```

`hanlint-disable-next`는 다음 블록 하나에 적용한다. 규칙 이름을 생략하면 그 범위의 규칙 전부에 적용한다.
프로젝트 전체에서 제외할 규칙은 설정의 `disable`에 적는다. 확정 오탐은 예외 처리와 함께
[개선 사례](../operation/feedback.md)로 남길 수 있다.

문서 형식에 맞춘 설정도 있다. 예를 들어 문장형 부제를 허용할 제목 깊이는 `headingSentenceMaxLevel`,
산문 검사에서 제외할 펜스 종류는 `ignoreFences`로 지정한다. 실제 설정 예시는 `hanlint init`이 만든다.

## 기존 문서에 도입하기

baseline은 현재 지적을 기록해 이후 검사에서 같은 지적을 제외한다. 기존 글을 모두 고칠 때까지
도입을 미루지 않고 새 변경부터 살필 때 쓴다.

```console
hanlint baseline 문서들/
hanlint 문서들/ --baseline
```

CI와 다른 검사에서도 계속 쓰려면 생성한 baseline 파일을 커밋하고 `hanlint.toml`에 연결한다.
파일을 만들기만 해서는 일반 검사에 자동 적용되지 않는다.

```toml
preset = "docs"
baseline = ".hanlint-baseline.json"
```

잠금은 줄 번호가 아닌 인용문을 기준으로 한다. 문단을 옮겨도 같은 문장은 유지되고, 문장을 고치거나
새로 쓰면 다시 검사한다. 삭제된 지적은 같은 파일 범위를 대상으로 정리한다.

```console
hanlint baseline 문서들/ --prune
```

baseline이 글의 품질을 승인하는 것은 아니다. 잠근 지적도 필요에 따라 다시 검토한다.

## 결과를 다른 도구에 전달하기

```console
hanlint 글.md --format compact --errors-only
hanlint 글.md --format json
hanlint 글.md --format github --errors-only
```

`compact`는 지적을 한 줄씩 보여 주고, `json`은 위치와 이유, 본보기와 제공할 수 있는 후보를 담는다.
`github`는 Actions에서 읽는 주석 형식이다. `--errors-only`는 notice 표시를 제외한다. 기본 text 출력은 확인할 자리
(notice) 를 규칙과 줄 번호 한 줄로 접는다. `--notices` 가 다 편다.
설정 안내 같은 주변 출력을 줄이려면 `--quiet`를 사용한다.

### 종료 코드

일반 검사는 error가 없으면 0, 하나라도 있으면 1이다. notice만 있어도 0이므로 결과 내용을 함께 읽는다.
잘못된 인자, 없는 파일이나 지원하지 않는 명령 같은 실행 오류는 2다.

`fix`의 0은 수정 명령이 정상 종료했다는 뜻이다. 남은 지적은 다시 검사한다. `check`와 `verify-patch`는
[계약의 위반과 검증 조건](readerContract.md)에 따라 종료한다. `hook`은 파일 쓰기나 답변을 막지 않도록
항상 0으로 끝난다. 모든 명령의 0을 글의 품질 판정으로 해석하지 않는다.

## 명령별 지원 범위

표의 명령은 Python에서 모두 실행할 수 있다. npm 칸이 ‘아니오’인 명령은 Python 패키지를 사용한다.
명령 누락과 npm 지원 여부는 실제 CLI를 실행하는 게이트로 확인한다.

| 명령 | 무엇 | npm |
|---|---|---|
| `hanlint` | 첫 화면. 이 폴더의 파일 이름으로 만든 예시와 다음 걸음 | 예 |
| `hanlint contract init 글.md --reader "독자" --goal "목표"` | 기존 글의 보호 표면에서 호환용 version 1 계약을 만든다 | 예 |
| `hanlint check contract.json 글.md --format text` | 보호 표면, 제목 구조, Finding, 글 요약과 다음 행동을 한 영수증으로 본다 | 예 |
| `hanlint verify-patch contract.json 글.md patch.json` | 이유가 붙은 정확 국소 치환이 새 위반을 만드는지 검증한다 | 예 |
| `hanlint watch 글.md` | 저장할 때마다 다시 검사한다 | 아니오 |
| `hanlint hook`, `hanlint hook --reply` | Claude Code가 저장한 마크다운과 마지막 답변을 같은 턴에 비차단 검사한다 | 예 |
| `hanlint fix 글.md` | 번역투, 명령형 뒤 마침표, 이중 부정처럼 확실한 자리를 고친다 | 예 |
| `hanlint explain <규칙>` | 규칙의 기술서와 본보기. 오타면 가까운 이름을 준다 | 예 |
| `hanlint patterns --rule <규칙>` | 그 규칙을 피하는 문장 틀. 예시는 error 0 이 보장된다 | 예 |
| `hanlint primer --preset docs` | 쓰기 전에 읽는 한 장. 켜진 규칙마다 고치는 법과 본보기 전후. 후는 error 0 이 보장된다 | 예 |
| `hanlint spec --preset blog --chars 800` | 같은 규칙판과 종류 프로파일을 쓰기 전 숫자 사양으로 편다 | 예 |
| `hanlint rules` | 규칙 목록. 부류로 묶고 꺼진 것을 표시한다 | 예 |
| `hanlint baseline 글들/` | 지금 있는 지적을 잠근다. `--prune` 은 죽은 잠금을 치운다 | 예 |
| `hanlint sheet src/ --preset screen` | 소스 (js, jsx, ts, rs, py, html, vue, svelte) 의 한국어 글을 표 하나로 떨군다. `--all` 은 지적 없는 글도 | 예 |
| `hanlint sheet apply 시트.md` | 표의 고침 칸을 파일의 그 자리에 되돌려 쓴다. `--dry-run` 은 보기만 | 예 |
| `hanlint doctor` | 어느 설정을 읽었고 어느 분석기로 돌며 어느 규칙이 꺼져 있는지 | 예 |
| `hanlint init --preset docs` | 글의 종류에 맞춘 `hanlint.toml` | 예 |
| `hanlint audit 글.md` | 지문 지도와 분포. 색이 있는 자리가 구멍이다 | 아니오 |
| `hanlint map 글.md --format html` | 지도를 단일 HTML 로 | 아니오 |
| `hanlint print 글.md --layer sentences` | 문장, 문단, 절, 글의 지문을 JSON 으로 | 예 |
| `hanlint diff 전.md 후.md` | 두 초안의 짜임, 리듬, 지적 수의 변화 | 아니오 |
| `hanlint learn 전.md 후.md` | 실제 고침에서 승인할 정확 재생 패치와 안전한 표면 치환 후보 | 아니오 |
| `hanlint packet 글.md` | 초안, 대조 분포, 독자 상태, 고침 근거를 AI용 JSON으로 컴파일 | 아니오 |
| `hanlint blueprint brief.json` | 1,600편의 종류별 분포에서 원문 없는 절·문단·문장·위치 예산을 만든다 | 아니오 |
| `hanlint evidence brief.json` | v2 brief의 사실별 고정 출처 판·인용 조각 해시·라이선스를 검증한다 | 아니오 |
| `hanlint entailment cases / evaluate` | gold 없는 36개 근거 쌍을 내고 외부 평가기의 3분류·기권 지표를 집계한다 | 아니오 |
| `hanlint guard brief.json 글.md` | 구조화 요구와 결과의 필수 표면·숫자·URL·코드·길이·error를 대조한다 | 아니오 |
| `hanlint arena panel / assign / review-page / assignment-record` | 같은 사실의 기준과 후보를 평가자별 단일 HTML로 눈가림하고, 회수한 독립 평가를 원래 방향으로 잠근다 | 아니오 |
| `hanlint profile build 글들/` | 참조 글의 분포 (프로파일). `--profile` 로 종류의 프로파일 대신 그것과 견준다 | 아니오 |
| `hanlint terms 글.md` | 한국어 학습용 어휘 C에만 등재된 화제어의 첫 자리를 찾는다. `--outside` 는 목록 밖 후보도 보인다 | 아니오 |
| `hanlint coverage review.json 글.md` | 사람 평가자의 지적 가운데 hanlint 가 같은 자리를 집은 비율 | 아니오 |

정확한 인자와 옵션은 `hanlint --help` 또는 `npx hanlint --help`에서 확인한다.
`spec`의 프로파일은 편집된 글에서 관찰한 분포이며 맞출 정답이 아니다. `chat`에는 비교할 프로파일이
없어 `spec`을 제공하지 않는다. 생성 결과의 사실 안전이나 자연스러움을 보장하지 않는다.

작문 패킷, 근거 평가와 사람 패널의 사용 절차는 [작문 축](../operation/writingAxis.md)이 소유한다.

직접 만든 프로파일은 `hanlint 새글.md --profile 우리문체.json`으로 사용한다. 종류가 섞인 글은
적절한 프리셋이나 참조 프로파일별로 나눠 검사한다. `terms`는 국립국어원이 공개한 한국어 학습용 어휘를
기준으로 설명이 필요할 수 있는 첫 등장을 찾는다. 모어 화자가 읽을 때의 난도나 글의 품질을 채점하지 않는다.

`learn` 결과는 승인 전 후보다. 사람이 뜻을 확인한 뒤 설정에 넣는 절차는
[승인한 고침 남기기](../operation/writingAxis.md#승인한-고침을-다음-글에-남기기-learn)에 있다.
브라우저의 수정 이력과 이 CLI 설정 파일은 서로 다른 형식이다. 브라우저 JSON을 그대로 TOML에 붙이지 않는다.
