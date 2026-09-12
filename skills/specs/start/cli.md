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

## 프리셋과 설정

글의 목적이 달라지면 프리셋부터 고른다. `blog`, `docs`, `report`, `guide`, `essay`, `fiction`,
`encyclopedia`, `chat`을 지원한다. `chat`은 대화 답변용이며 문서의 짜임을 재는 규칙을 줄인다.
기본값과 꺼지는 규칙은 [설정 코드](../../../src/hanlint/config/settings.py)와 실행 결과에서 확인한다.

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
`github`는 Actions에서 읽는 주석 형식이다. `--errors-only`는 notice 표시를 제외한다.
설정 안내 같은 주변 출력을 줄이려면 `--quiet`를 사용한다.

### 종료 코드

일반 검사는 error가 없으면 0, 하나라도 있으면 1이다. notice만 있어도 0이므로 결과 내용을 함께 읽는다.
잘못된 인자, 없는 파일이나 지원하지 않는 명령 같은 실행 오류는 2다.

`fix`의 0은 수정 명령이 정상 종료했다는 뜻이다. 남은 지적은 다시 검사한다. `check`와 `verify-patch`는
[계약의 위반과 검증 조건](readerContract.md)에 따라 종료한다. `hook`은 파일 쓰기나 답변을 막지 않도록
항상 0으로 끝난다. 모든 명령의 0을 글의 품질 판정으로 해석하지 않는다.

## 공통 명령 선택

| 작업 | 명령 |
|---|---|
| 검사·확정 수정 | `hanlint 글.md`, `hanlint fix 글.md` |
| 규칙 설명·본보기·문형 | `hanlint rules`, `hanlint explain nounPile`, `hanlint patterns --rule nounPile` |
| 쓰기 전 규칙 안내 | `hanlint primer --preset docs` |
| 종류별 분포와 현재 규칙 임계 확인 | `hanlint spec --preset blog --chars 800` |
| 문장 지문 보기 | `hanlint print 글.md --layer sentences` |
| 설정·기존 지적 관리 | `hanlint init`, `hanlint doctor`, `hanlint baseline 문서들/` |
| 명시한 원문 보호와 국소 치환 확인 | `hanlint contract init`, `hanlint check`, `hanlint verify-patch` |
| 에이전트가 쓴 파일·답변 검사 | `hanlint hook`, `hanlint hook --reply` |

정확한 인자와 옵션은 `hanlint --help` 또는 `npx hanlint --help`에서 확인한다.
`spec`의 프로파일은 편집된 글에서 관찰한 분포이며 맞출 정답이 아니다. `chat`에는 비교할 프로파일이
없어 `spec`을 제공하지 않는다. 생성 결과의 사실 안전이나 자연스러움을 보장하지 않는다.

## Python 전용 작업

다음 명령은 Python 패키지로 실행한다. npm CLI에서 호출하면 Python을 사용하라는 안내가 나온다.

| 작업 | 명령과 안내 |
|---|---|
| 파일 저장 때 재검사 | `hanlint watch 글.md` |
| 지문 지도와 분포 | `hanlint audit 글.md`, `hanlint map 글.md --format html` |
| 두 초안 비교 | `hanlint diff 전.md 후.md` |
| 승인할 수정 후보 추출 | `hanlint learn 전.md 후.md --format toml` |
| 참조 글의 문체 분포 만들기 | `hanlint profile build 승인된글들/ --output 우리문체.json` |
| 학습자가 확인할 어휘 후보 | `hanlint terms 글.md`, `hanlint terms 글.md --outside --format json` |
| 사람 지적과 검사기 지적의 겹침 | `hanlint coverage review.json 글.md` |
| 작문 패킷·요구 대조·구조 실험 | `packet`, `guard`, `blueprint`. [작문 축](../operation/writingAxis.md) |
| 근거 원장과 외부 평가기 측정 | `evidence`, `entailment`. [작문 축](../operation/writingAxis.md) |
| 사람 패널과 자동 심사기 비교 | `arena`. [평가 절차](../operation/writingAxis.md#사람-평가-arena) |

직접 만든 프로파일은 `hanlint 새글.md --profile 우리문체.json`으로 사용한다. 종류가 섞인 글은
적절한 프리셋이나 참조 프로파일별로 나눠 검사한다. `terms`는 국립국어원이 공개한 한국어 학습용 어휘를
기준으로 설명이 필요할 수 있는 첫 등장을 찾는다. 모어 화자가 읽을 때의 난도나 글의 품질을 채점하지 않는다.

`learn` 결과는 승인 전 후보다. 사람이 뜻을 확인한 뒤 설정에 넣는 절차는
[승인한 고침 남기기](../operation/writingAxis.md#승인한-고침을-다음-글에-남기기-learn)에 있다.
브라우저의 수정 이력과 이 CLI 설정 파일은 서로 다른 형식이다. 브라우저 JSON을 그대로 TOML에 붙이지 않는다.
