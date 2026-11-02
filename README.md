<p align="center">
  <a href="https://eddmpython.github.io/hanlint/"><img src="https://raw.githubusercontent.com/eddmpython/hanlint/main/web/brand.png" width="64" height="64" alt="한린트"></a>
</p>

# 한린트 · hanlint

**고칠 곳이 보이는 한국어 글쓰기.**
글을 넣으면 번역투, 명사 나열, 이중 피동과 문서 안의 어긋남을 찾아 **문장, 이유, 고친 예시**를 보여 준다.
앱의 화면 글(버튼, 라벨, 상태)은 프리셋 `screen`으로 검사한다. 단어 하나면 될 곳에 쓴 문장과 화면을 설명하는 글을 잡고, `hanlint sheet`가 소스 전체의 글을 표 하나로 모은다.
직접 고친 내용을 비교하고, 다시 쓰고 싶은 고침은 뜻을 확인한 뒤 기억할 수 있다.

[![PyPI](https://img.shields.io/pypi/v/hanlint?label=pypi)](https://pypi.org/project/hanlint/)
[![npm](https://img.shields.io/npm/v/hanlint?label=npm)](https://www.npmjs.com/package/hanlint)
[![CI](https://github.com/eddmpython/hanlint/actions/workflows/ci.yml/badge.svg)](https://github.com/eddmpython/hanlint/actions/workflows/ci.yml)
[![Pages](https://github.com/eddmpython/hanlint/actions/workflows/pages.yml/badge.svg)](https://github.com/eddmpython/hanlint/actions/workflows/pages.yml)

**[지금 글 다듬기][editor]** · [저장과 사용 안내][guide] · [명령과 설정][cli] · [npm API][npm] · [변경 이력][changes]

## 설치 없이 바로 써 보기

[브라우저 편집기][editor]를 열면 예문과 실제 지적이 바로 나온다. 계정이나 API 키 없이 검사할 수 있다.

1. 왼쪽 원문에 내 글을 붙여 넣거나 파일을 연다. 오른쪽에 검사 결과가 나온다.
2. 결과에 바로 표시된 이유와 예시를 읽는다. 고침 버튼을 누르면 아래 수정본에 반영된다.
3. 원문이 미리 담긴 아래 수정본을 바로 다듬고 한 번 눌러 기록한다. 수정 전 원문은 보존된다.
4. 수정본 아래에 원문 보호와 기억할 고침이 나타난다. 다시 제안받을 고침은 뜻을 확인하고 승인한다.

다크·라이트는 시스템 설정을 따르고 우상단 버튼으로 전환한다. 선택한 테마는 다음 방문에도 유지된다.

검사는 브라우저 안에서 실행한다. 원고와 수정 이력은 브라우저에 보관되며, 선택하면 파일로 내보내거나
개인 GitHub 저장소에 저장할 수 있다. GitHub 보관에는 원고를 저장할 저장소의 Contents 읽기·쓰기 토큰이 필요하다.
토큰은 현재 탭의 메모리에만 둔다. 저장 한도, 가져오기와 충돌 처리는 [저장과 사용 안내][guide]에 있다.

**수정 이력, 재사용 승인, 공통 규칙 개선은 서로 다른 단계다.** 수정본을 기록한 것만으로 정답 데이터가
되지는 않는다. 승인한 고침은 같은 원문과 문맥에서 제안하고, 공통 규칙에 기여할 사례는 따로 선택해 내보낸다.

## 내 작업에 맞는 입구

| 하고 싶은 일 | 시작하는 곳 |
|---|---|
| 글을 붙여 넣고 바로 다듬기 | [브라우저 편집기][editor] |
| 앱의 화면 글을 표 하나로 보기 | [브라우저 편집기][editor]에 GitHub 저장소 주소 붙여 넣기, 또는 `hanlint sheet src/ --preset screen` |
| 실제 글에서 단어의 쓰임 보기(AI가 쓰기 전에 묻는다) | `hanlint usage "낱말" --kind report`가 함께 쓰는 말과 문장을 낸다. 색인은 `hanlint usage build <종류> 글들/` |
| 마크다운 파일과 폴더 검사 | Python의 `hanlint 글.md` 또는 Node의 `npx hanlint 글.md` |
| 앱에서 검사 결과 사용 | Python의 `lintText`, [npm 공개 API][npm] |
| 문서 변경을 커밋과 CI에서 검사 | [pre-commit과 GitHub Actions][integrations] |
| AI가 쓴 파일과 답변에 지적 전달 | [에이전트 스킬과 훅][integrations] |
| 숫자, 링크와 제목 순서를 명시적으로 보호 | [Reader Contract][contract] |
| 내 계정에서 브라우저 편집기 운영 | [Fork와 GitHub Pages][fork] |

Python과 npm은 공통 명령에서 같은 규칙과 출력을 사용하며, 런타임 의존성이 없다.
브라우저는 같은 npm 엔진으로 검사한다. `audit`의 색 지도, 초안 비교와 평가 도구 등 Python 전용 명령의 범위는
[명령 안내][cli]에서 확인할 수 있다.

## 터미널에서 첫 검사

Python 3.11 이상이면 설치 후 파일을 검사한다.

```console
pip install hanlint
hanlint 글.md
hanlint sheet src/ --preset screen
```

둘째 줄은 앱의 화면 글이다. 소스 파일의 한국어 문자열과 JSX 글을 표 하나로 내보내고, 표의 고침 칸을 채워
`hanlint sheet apply 시트.md`로 되돌려 쓴다.

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
일반 검사의 종료 코드는 오류 지적이 없으면 0, 있으면 1, 잘못된 인자나 실행 실패는 2다.
경고는 읽어 보고 판단할 지적이다. 명령별 예외는 [종료 코드 안내][exitCodes]에 있다.

## 무엇을 짚나

| 검사할 표현이나 상황 | 확인하는 것 |
|---|---|
| `결과가 저장되어집니다.` | 이중 피동. `결과가 저장됩니다.`로 고칠 수 있다 |
| `가상환경 생성 후 패키지 설치 확인 절차` | 조사 없이 이어지는 명사와 빠진 관계 |
| 앞 문장에 대상이 없는 지시어 | 독자가 앞에서 받은 정보로 대상을 찾을 수 있는지 |
| 도입에서 약속한 개수와 다른 목록 | 문서 안에서 세는 값이 맞는지 |
| 만들지 않은 파일을 읽는 예제 | 따라 하는 독자가 필요한 파일을 얻었는지 |
| 화면의 `요청을 완료하지 못했습니다` | 단어 하나면 될 곳에 쓴 문장(프리셋 `screen`). `요청 실패` 한 단어로 쓴다 |
| 화면의 `신청이 오면 여기에 표시됩니다` | 아직 빈 곳을 미리 알리는 화면 설명. 빈 상태는 `요청 없음`으로 쓴다 |
| 화면의 `계약 메타데이터` | 개발자가 쓰는 말. 사용자가 쓰는 `계약 정보`로 바꾼다. 프로젝트가 정한 단어(`회사` → `수임처`)는 설정의 사전에 넣는다 |

지적에는 위치와 규칙 이름, 인용 문장, 이유가 붙는다. 예시는 글의 종류와 합니다체·한다체·해요체에
맞춰 보여 준다. 예시는 다시 쓰는 방법을 설명하는 사례이며, 내 문장에 그대로 적용할 답은 직접 고른다.

```console
hanlint explain nounPile
hanlint patterns --rule nounPile
hanlint rules --preset docs
```

한린트는 좋은 글의 점수나 등급을 내지 않는다. 맞춤법 전체, 사실의 진실, 의미 보존과 자연스러움은 판단하지
않는다. 어떤 결함을 늘 같은 기준으로 검사하고 어떤 것은 다루지 않는지는 [제품 경계][product]에 정리돼 있다.

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
| Contract | 독자, 목표, 승인한 사실과 지켜야 할 숫자·링크·코드, 제목 구조를 적는다 |
| Finding | 검사기가 짚은 위치와 이유를 알린다 |
| Patch | 지적 하나를 없애도록 글의 한 곳을 정확히 바꾸는 고침을 제안한다 |

예를 들어 H2 제목이 있는 초안에서 제목 수와 순서를 고정하려면 다음과 같이 실행한다.

```console
hanlint contract init 초안.md --reader "개발자" --goal "라이브러리를 비교한다" --outline h2 --output contract.json
hanlint check contract.json 초안.md --format text
```

생성한 계약은 사람이 확인한다. 제목이 없는 자유 원고는 브라우저에서 바로 비교할 수 있다.
계약 버전, 보호 범위, 입력 조건과 실행 가능한 API 예제는 [Reader Contract 프로토콜][contract]에 있다.

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
| [Reader Contract][contract] | 입력 스키마, 결과 JSON, 고정할 사실과 수정 범위 |
| [작문 실험과 평가][writingAxis] | brief, packet, guard, arena의 절차와 검증 범위 |
| [개발·운영 문서][skills] | 코드 구조, 기여, 검증, 패키지와 Pages 배포 |

작문 패킷과 평가 도구는 글이 자연스러워진다는 근거가 아직 없어 기본 절차에 넣지 않았다.
실험 결과와 적용 범위는 [작문 실험과 평가][writingAxis]와 [실측 기록][attempts]에서 확인할 수 있다.

## AI 에이전트를 위한 한국어 글쓰기 지침

에이전트가 쓴 한국어에는 되풀이되는 표현이 있다. 그 표현을 사람 글과 비교해 세고, 그 가운데 기계가 잡을 수 있는
것만 규칙으로 만들었다. 재료는 사람이 쓴 한국어 155만 문장(위키백과 본문·지침·토론과 사업보고서, 네 장르)과
기계가 쓴 360편이다.

글쓰기 지침 `src/hanlint/data/koreanProse.txt`의 앞 여섯 항목이 그 결과다. 아래 표는 그 여섯 항목을 일곱 줄로 나눠
(3번 항목의 `그다음`과 `첫 번째는`을 따로 셌다) 사람과 기계의 비율을 붙였다. 표본을 늘려 차이가 사라진 항목은
다시 본다. 일곱째 항목은 과잉 교정을 막는다. `hanlint primer`가 이 지침을 첫머리에 싣고, 에이전트 훅에
`hanlint hook --prime`을 걸면 세션 문맥에 실린다.

| 지침 | 사람 | 기계 | 배수 | 기계 검사 |
|---|---|---|---|---|
| `~하는 이유가 여기 있다`로 설명을 가리키지 않는다 | 0.01 | 6.30 | 630배 | `cliche` |
| 문장을 `그다음`으로 시작해 번호를 매기지 않는다 | 0.06 | 6.93 | 116배 | `cliche` |
| `X가 아니라 Y다`를 남발하지 않는다 | 7.05 | 65.55 | 9.3배 | `phraseRepeat` |
| 산문 안에서 `첫 번째는`으로 번호를 매기지 않는다 | 0.22 | 9.14 | 42배 | 없음 |
| `~하는 편이 낫다`로 권고를 흐리지 않는다 | 0.47 | 16.07 | 34배 | 없음 |
| `~인 셈이다`로 되짚지 않는다 | 0.13 | 4.10 | 32배 | 없음 |
| 긴 문장을 아예 안 쓰면 기계 글이다 | 4.6~15.5% | 0.2~0.3% | 15~23배 | 없음 |

(천 문장당 비율. 사람 쪽은 네 장르 가운데 가장 높은 값이다. 마지막 줄만 글 안의 문장 비율이다)

**일곱 줄 가운데 셋만 기계가 검사한다.** 넷은 글자 모양만으로 바르게 쓴 문장과 가를 수 없다. `~인 셈이다`가
걸린 사람 글의 문장(`10년 걸린 셈입니다`)은 모두 바르게 쓴 것이었고, `~하는 편이 낫다`를 문장마다 짚으면
사람 글의 3.31%가 걸린다. 마지막 줄은 글 한 편에서 재는 값이라 문장 하나를 잘못 짚는 문제는 없어 보였다.
그러나 산문이 8문장 이상인 사람 글 4,021편 가운데 **30.2%에 긴 문장이 하나도 없다** (16문장 이상으로 좁혀도
19.5%). 사람 글 다섯 편 가운데 한 편을 잡는 검사는 규칙으로 둘 수 없다. 이 표는 규칙으로 잡지 못하는 것도
그대로 적어 둔다.

### 효과를 잰 실험

용어 보존 문장을 더하기 전의 글쓰기 지침을 읽고 쓴 글과 읽지 않고 쓴 글을 같은 주제로 만들고, 어느 쪽 글인지
가린 채 비교했다. 지금 문구가 더하는 효과는 따로 재지 않았다. 판정 조건은 실험을 돌리기 **전에**
적었다 (`tests/_attempts/craftLift/probeCraftLift_log.md`).

| 회차 | 필자 | 과제 | 지침 | 대조 | 부호검정 p | 판정 |
|---|---|---|---|---|---|---|
| 1 | claude-opus-5 | 48 | 31 | 17 | 0.0595 | 기준에 못 미쳤고, 기준을 낮추지 않았다 |
| 2 | claude-opus-5 | 96 | **67** | **29** | **0.0001** | 채택 |
| 필자 교체 | Codex(gpt-5.6-sol) | 96 | **90** | **6** | **0.0000** | 채택 |

2회차는 1회차와 주제가 겹치지 않고 수를 합치지도 않은 독립 시험이다. 심판은 지침도 규칙 이름도 받지 않았고
글의 차례는 과제마다 섞였다. 필자 교체 회차는 필자만 Codex로 바꾸고 심판은 claude-opus-5로 두었다. 같은 카테고리를
받은 Codex 심판도 77 대 19로 지침을 읽은 글을 골랐다 (`tests/_attempts/codexCraft/probeCodexCraft_log.md`).

두 회차 모두 이긴 까닭이 같다. 지침을 읽은 글에는 **숫자와 동작이 나온다** (`수분 15퍼센트와
30퍼센트`, `이슬점 12도`, `가구를 5센티미터 띄우라`). 지침에 `구체적으로 써라`라는 줄은 없다.
지침의 4번 항목(`~하는 편이 낫다`)이 얼버무리는 말을 막으니 단정해야 하고, 단정하려면 숫자와 동작을 들어야 한다.

### 규칙의 오탐

규칙 둘을 사람 글 5,150편과 기계 글 360편에 돌려 잰 값이다.

| 규칙 | 사람 글 | 기계 글 | 배수 |
|---|---|---|---|
| `phraseRepeat` | 0.12% | 20.28% | 174배 |
| `cliche`의 새 항목 둘 | 0.14% | 10.83% | 80배 |

사람 글 800편에 한 편꼴로 걸린다. `phraseRepeat`는 같은 문형이 **두 번 이상** 나오고 글 안의 비율이 8%를
넘을 때만 짚는다. 한 번 쓴 글은 짚지 않는다.

### 직접 재 보기

```console
python -X utf8 -B tests/_attempts/aiTells/probeAiTells.py many <기계 글 폴더>
python -X utf8 -B tests/_attempts/aiTells/probeDensity.py --ai <기계 글 폴더>
python -X utf8 -B tests/_attempts/aiTells/probeRuleReach.py --ai <기계 글 폴더>
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py follow <시험 폴더>
```

말뭉치는 `scripts/fetch/`가 받는다 (위키백과는 `--namespaces`로 장르를 고른다). 잰 것과 **못 잰 것과 버린
것**은 [실측 기록][attempts]에 있다. 이 실험에서 버린 규칙이 남긴 규칙보다 많다.

## 오탐과 개선 사례

바르게 쓴 문장이 잡혔으면 [오탐 신고][issues]에 문장, 규칙 이름, 사용한 버전과 글 종류를 남긴다.
앞뒤 문맥이 필요하면 공개할 수 있는 범위로 함께 적는다. 브라우저에서 기록한 수정 사례도 선택해서
내보낼 수 있다. [기여 절차][feedback]에 따라 사례를 검토한 뒤 규칙이나 예시를 고친다.

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
| 브라우저의 Pretendard 글꼴 | [SIL OFL 1.1](web/pretendard.LICENSE.txt) |

npm과 브라우저에는 쉬운 말 자료의 파생물이 포함된다. 브라우저의 자료와 글꼴 고지는
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
