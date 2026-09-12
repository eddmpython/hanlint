<p align="center">
  <a href="https://eddmpython.github.io/hanlint/"><img src="https://raw.githubusercontent.com/eddmpython/hanlint/main/web/brand.svg" width="64" height="64" alt="한린트"></a>
</p>

# 한린트 · hanlint

**고칠 곳이 보이는 한국어 글쓰기.**
글을 넣으면 번역투, 명사 나열, 이중 피동과 문서 안의 어긋남을 찾아 **문장, 이유, 고친 본보기**를 보여 준다.
직접 고친 내용을 비교하고, 다시 쓰고 싶은 고침은 뜻을 확인한 뒤 기억할 수 있다.

[![PyPI](https://img.shields.io/pypi/v/hanlint?label=pypi)](https://pypi.org/project/hanlint/)
[![npm](https://img.shields.io/npm/v/hanlint?label=npm)](https://www.npmjs.com/package/hanlint)
[![CI](https://github.com/eddmpython/hanlint/actions/workflows/ci.yml/badge.svg)](https://github.com/eddmpython/hanlint/actions/workflows/ci.yml)
[![Pages](https://github.com/eddmpython/hanlint/actions/workflows/pages.yml/badge.svg)](https://github.com/eddmpython/hanlint/actions/workflows/pages.yml)

**[지금 글 다듬기][editor]** · [저장과 사용 안내][guide] · [명령과 설정][cli] · [npm API][npm] · [변경 이력][changes]

## 설치 없이 바로 써 보기

[브라우저 편집기][editor]를 열면 예문과 실제 지적이 바로 나온다. 계정이나 API 키 없이 검사할 수 있다.

1. 예문을 전체 선택해 내 글을 붙여 넣거나 파일을 연다. 붙여 넣은 글이 수정 전 원문이 된다.
2. 지적의 이유와 본보기를 읽는다. 확정할 수 있는 표현은 버튼으로 고치고, 나머지는 직접 수정한다.
3. 전후 비교와 원문 보호에서 바뀐 내용을 확인하고 수정본을 기록한다.
4. 다시 제안받을 고침은 고침 기억에서 뜻을 확인하고 승인한다.

검사는 브라우저 안에서 실행한다. 원고와 수정 이력은 브라우저에 보관되며, 선택하면 파일로 내보내거나
개인 GitHub 저장소에 저장할 수 있다. GitHub 보관에는 원고를 저장할 저장소의 Contents 읽기·쓰기 토큰이 필요하다.
토큰은 현재 탭의 메모리에만 둔다. 저장 한도, 가져오기와 충돌 처리는 [저장과 사용 안내][guide]에 있다.

**수정 이력, 재사용 승인, 공통 규칙 개선은 서로 다른 단계다.** 수정본을 기록한 것만으로 정답 데이터가
되지는 않는다. 승인한 고침은 같은 원문과 문맥에서 제안하고, 공통 규칙에 기여할 사례는 따로 선택해 내보낸다.

## 내 작업에 맞는 입구

| 하고 싶은 일 | 시작하는 곳 |
|---|---|
| 글을 붙여 넣고 바로 다듬기 | [브라우저 편집기][editor] |
| 마크다운 파일과 폴더 검사 | Python의 `hanlint 글.md` 또는 Node의 `npx hanlint 글.md` |
| 앱에서 검사 결과 사용 | Python의 `lintText`, [npm 공개 API][npm] |
| 문서 변경을 커밋과 CI에서 검사 | [pre-commit과 GitHub Actions][integrations] |
| AI가 쓴 파일과 답변에 지적 전달 | [에이전트 스킬과 훅][integrations] |
| 숫자, 링크와 제목 순서를 명시적으로 보호 | [Reader Contract][contract] |
| 내 계정에서 편집기 운영 | [Fork와 GitHub Pages][fork] |

Python과 npm은 공통 명령에서 같은 규칙과 출력을 사용하며, 런타임 의존성이 없다.
브라우저는 같은 npm 엔진으로 검사한다. 지문 지도, 초안 비교와 평가 도구 등 Python 전용 명령의 범위는
[명령 안내][cli]에서 확인할 수 있다.

## 터미널에서 첫 검사

Python 3.11 이상이면 설치 후 파일을 검사한다.

```console
pip install hanlint
hanlint 글.md
```

Node 18 이상이면 다음 명령으로 같은 검사를 실행한다.

```console
npx hanlint 글.md
```

`hanlint` 또는 `npx hanlint`만 실행하면 현재 폴더의 마크다운 이름으로 만든 사용 예가 나온다.
파일 대신 폴더를 주면 하위 마크다운까지 검사한다.

```console
hanlint 문서들/ --preset docs
hanlint fix 글.md
hanlint 글.md --format json
```

`fix`는 원본 파일을 고친다. 적용 뒤에도 남은 지적과 문장의 뜻을 확인한다.
일반 검사의 종료 코드는 error가 없으면 0, 있으면 1, 잘못된 인자나 실행 오류는 2다.
notice는 읽고 판단할 참고 지적이다. 명령별 예외는 [종료 코드 안내][exitCodes]에 있다.

## 어떤 자리를 보여 주나

| 검사할 표현이나 상황 | 확인하는 것 |
|---|---|
| `결과가 저장되어집니다.` | 이중 피동. `결과가 저장됩니다.`로 고칠 수 있다 |
| `가상환경 생성 후 패키지 설치 확인 절차` | 조사 없이 이어지는 명사와 빠진 관계 |
| 앞 문장에 대상이 없는 지시어 | 독자가 앞에서 받은 정보로 대상을 찾을 수 있는지 |
| 도입에서 약속한 개수와 다른 목록 | 문서 안에서 세는 값이 맞는지 |
| 만들지 않은 파일을 읽는 예제 | 따라 하는 독자가 필요한 파일을 얻었는지 |

지적에는 위치와 규칙 이름, 인용 문장, 이유가 붙는다. 본보기는 글의 종류와 합니다체·한다체·해요체에
맞춰 보여 준다. 본보기는 다시 쓰는 방법을 설명하는 사례이며, 내 문장에 그대로 적용할 답은 직접 고른다.

```console
hanlint explain nounPile
hanlint patterns --rule nounPile
hanlint rules --preset docs
```

한린트는 좋은 글의 점수나 등급을 내지 않는다. 맞춤법 전체, 사실의 진실, 의미 보존과 자연스러움은 판단하지
않는다. 어떤 결함을 결정적으로 검사하고 어떤 것은 다루지 않는지는 [제품 경계][product]에 정리돼 있다.

## 글 종류부터 고르기

블로그, 기술 문서, 보고서, 안내서, 수필, 소설, 백과와 대화에 맞는 프리셋이 있다. 문서 한 편에만 적용하거나
프로젝트 설정으로 남길 수 있다.

```console
hanlint 명세.md --preset docs
hanlint init --preset docs
hanlint doctor
```

이미 문서가 쌓인 저장소에는 baseline으로 기존 지적을 기록하고 새 지적부터 볼 수 있다.
설정 방법과 주의할 범위는 [프리셋, 예외와 baseline][cli]를 따른다.

## Contract, Finding, Patch

모델이나 편집기에서 재작성 범위를 확인할 때 쓰는 공개 프로토콜이다.

| 개념 | 역할 |
|---|---|
| Contract | 독자, 목표, 승인한 사실과 보호할 표면·구조를 선언한다 |
| Finding | 검사기가 집은 위치와 이유를 전달한다 |
| Patch | 기존 지적 하나를 줄이는 정확한 국소 치환을 제안한다 |

예를 들어 H2 제목이 있는 초안에서 제목 수와 순서를 잠그려면 다음과 같이 실행한다.

```console
hanlint contract init 초안.md --reader "개발자" --goal "라이브러리를 비교한다" --outline h2 --output contract.json
hanlint check contract.json 초안.md --format text
```

생성한 계약은 사람이 확인한다. 제목이 없는 자유 원고는 브라우저에서 바로 비교할 수 있다.
계약 버전, 보호 범위, 입력 조건과 실행 가능한 API 예제는 [Reader Contract 프로토콜][contract]이 소유한다.

## Python과 JavaScript에서

Python은 패키지의 공개 진입점에서 가져온다.

```python
from hanlint import lintText

text = "결과가 저장되어집니다."
for finding in lintText(text):
    print(finding.line, finding.rule, finding.why)
```

JavaScript는 `npm install hanlint` 후 ESM으로 가져온다.

```js
import { lintText } from "hanlint";

const text = "결과가 저장되어집니다.";
for (const finding of lintText(text)) {
  console.log(finding.line, finding.rule, finding.why);
}
```

브라우저 편집기는 main의 소스로 배포한다. 패키지는 릴리즈 때 배포하므로 시점이 다를 수 있다.
새 API의 배포 상태는 [npm 안내][npm]와 [Unreleased 변경][changes]를 함께 확인한다.

## 더 필요한 안내

| 안내 | 내용 |
|---|---|
| [브라우저 사용과 저장][guide] | 원문 비교, 수정 기록, 승인 고침, 개인 GitHub, 문제 해결 |
| [명령과 설정][cli] | 프리셋, 출력, baseline, Python 전용 명령 |
| [자동화 연결][integrations] | GitHub Actions, pre-commit, 에이전트 스킬, Claude Code 훅 |
| [Reader Contract][contract] | 입력 스키마, 영수증, 사실 잠금과 수정 범위 |
| [작문 실험과 평가][writingAxis] | brief, packet, guard, arena의 절차와 검증 범위 |
| [개발·운영 문서][skills] | 코드 구조, 기여, 검증, 패키지와 Pages 배포 |

작문 패킷과 평가 도구는 자연스러움 향상이 입증된 기본 작법으로 제공하지 않는다.
실험 결과와 적용 경계는 [작문 축][writingAxis]과 [실측 기록][attempts]에서 확인할 수 있다.

## 오탐과 개선 사례

정당한 문장이 잡혔으면 [오탐 신고][issues]에 문장, 규칙 이름, 사용한 버전과 글 종류를 남긴다.
앞뒤 문맥이 필요하면 공개할 수 있는 범위로 함께 적는다. 브라우저에서 기록한 수정 사례도 선택해서
내보낼 수 있다. [기여 절차][feedback]에 따라 사례를 검토한 뒤 규칙이나 본보기를 고친다.

## English

hanlint is a Korean prose linter for Markdown, with a browser editor, Python package and Node.js CLI.
It reports translationese, noun pile-ups, double passives and document inconsistencies, with locations,
reasons and rewriting examples. The browser runs the same npm engine locally and keeps revision history
separate from explicitly approved corrections.

Python and npm share deterministic rules with zero runtime dependencies. Reader Contracts can protect
numbers, URLs, inline code, links and heading order. These checks do not judge truth, meaning or writing quality.
[Try the editor][editor], use `pip install hanlint`, or run `npx hanlint draft.md`.

## 라이선스

| 대상 | 라이선스와 고지 |
|---|---|
| 코드와 나머지 데이터 | [MIT][license] |
| KLUE-NLI 파생 근거 평가 사례 | [CC BY-SA 4.0][klueLicense] |
| 국립국어원 학습용 어휘와 쉬운 말 자료 | [공공누리 제1유형][koglLicense] |

npm과 브라우저에는 외부 자료 중 쉬운 말 자료의 파생물이 포함된다. 브라우저의 고지는
[자료 출처와 라이선스][siteLicense]에서 읽을 수 있다. 기준 말뭉치 원문은 제품에 배포하지 않는다.

[editor]: https://eddmpython.github.io/hanlint/
[guide]: https://eddmpython.github.io/hanlint/guide.html
[fork]: https://eddmpython.github.io/hanlint/guide.html#fork
[cli]: https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/cli.md
[exitCodes]: https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/cli.md#종료-코드
[integrations]: https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/integrations.md
[npm]: https://github.com/eddmpython/hanlint/blob/main/npm/README.md
[contract]: https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/readerContract.md
[product]: https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/product.md
[writingAxis]: https://github.com/eddmpython/hanlint/blob/main/skills/specs/operation/writingAxis.md
[skills]: https://github.com/eddmpython/hanlint/blob/main/skills/README.md
[attempts]: https://github.com/eddmpython/hanlint/tree/main/tests/_attempts
[feedback]: https://github.com/eddmpython/hanlint/blob/main/skills/specs/operation/feedback.md
[issues]: https://github.com/eddmpython/hanlint/issues/new/choose
[changes]: https://github.com/eddmpython/hanlint/blob/main/CHANGELOG.md
[license]: https://github.com/eddmpython/hanlint/blob/main/LICENSE
[klueLicense]: https://github.com/eddmpython/hanlint/blob/main/src/hanlint/data/evidenceEntailmentV1.LICENSE.md
[koglLicense]: https://github.com/eddmpython/hanlint/blob/main/src/hanlint/data/koglType1.LICENSE.md
[siteLicense]: https://eddmpython.github.io/hanlint/license.html
