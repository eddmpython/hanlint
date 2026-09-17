# hanlint

한국어 글에서 반복되는 결함을 찾는 린터다. 번역투, 상투어, 이중 피동과 문장 구조를 검사하고,
지적마다 위치, 이유와 고칠 수 있는 표기를 돌려준다. Node.js 18 이상에서 런타임 의존성 없이 실행한다.

**[설치 없이 써 보기](https://eddmpython.github.io/hanlint/)** ·
[전체 소개](https://github.com/eddmpython/hanlint#readme) ·
[명령과 설정](https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/cli.md) ·
[변경 이력](https://github.com/eddmpython/hanlint/blob/main/CHANGELOG.md)

## 빠른 시작

```sh
npx hanlint 글.md
npx hanlint docs/ --preset docs
npx hanlint 글.md --format json
npx hanlint sheet src/ --preset screen
```

인자 없이 실행하면 현재 폴더의 파일을 바탕으로 시작 안내를 보여 준다.
파일 대신 폴더를 주면 아래의 마크다운 파일을 찾는다. 표준 입력은 `npx hanlint - --path 글.md`로 받는다.

```sh
npx hanlint fix 글.md
npx hanlint 글.md
```

`fix`는 고친 표기가 확정된 자리를 **파일에 직접 반영**한다. 변경을 확인하고 다시 검사한다.
일반 검사는 error가 없으면 0, 있으면 1, 입력이나 설정이 잘못되면 2로 끝난다.
notice만 있으면 0이며, `--errors-only`를 주면 notice 표시를 제외한다.
명령마다 다른 판정은 [종료 코드 안내](https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/cli.md#종료-코드)를 따른다.

## JavaScript에서 검사하기

```sh
npm install hanlint
```

```js
import { configFromMapping, lintText } from "hanlint";

const text = "이 도구는 다양한 기능을 제공합니다.";
const config = configFromMapping({ preset: "docs" });
for (const finding of lintText(text, config)) {
  console.log(finding.line, finding.rule, finding.why);
}
```

파일은 `lintFile("글.md", config)`로 검사한다. `loadConfig()`는 현재 위치에서 프로젝트 설정을 찾는다.
파일과 설정 경로를 읽는 API는 Node 전용이다. 문자열 API에 설정을 생략하면 기본 설정을 쓴다.

`blog`, `report`, `docs`, `guide`, `essay`, `fiction`, `encyclopedia`, `chat`, `screen`의 아홉 프리셋이 있다.
`screen`은 화면의 글 (단추, 이름표, 상태, 빈 상태) 이다. 낱말 자리의 문장과 화면 해설, 접객 말투를 잡고 산문 규칙은 끈다.
프로젝트 설정은 `npx hanlint init --preset docs`로 만들고 `npx hanlint doctor`로 확인한다.
규칙 목록은 `npx hanlint rules`, 개별 규칙의 근거는 `npx hanlint explain translationese`에서 본다.

## 수정하면서 원문 보호하기

Reader Contract는 사람이 확인한 독자, 목적과 사실을 받아 숫자, URL, 인라인 코드와 링크 목적지를 보호한다.

```js
import { Contract, Patch, check, renderCheck, verifyPatch } from "hanlint";

const text = "예산은 400,000원이다.";
const contract = new Contract(
  "배포를 결정할 운영자",
  "예산을 확인한다",
  ["예산은 380,000원이다."],
);
console.log(renderCheck(check(text, contract)));

const patch = new Patch("unexpectedNumbers", "400,000", "380,000");
const result = verifyPatch(text, patch, contract);
console.log(result);
```

`contractFromText(text, reader, goal)`은 원문에서 사실 후보를 모은다. 사람이 확인한 뒤 사용한다.
`contractFromTextV2(text, reader, goal, 2)`는 H2 제목의 수와 순서도 보호할 계약을 만든다.
패치는 원문 한 자리에 정확히 맞고 기존 위반을 줄이며 새 보호 위반이나 error를 만들지 않아야 검증된다.
사실의 진실, 의미 보존과 자연스러움은 사람이 판단한다.

JSON 형식과 전체 조건은
[Reader Contract](https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/readerContract.md)가 정본이다.

## 브라우저와 수정 사례

[한린트 편집기](https://eddmpython.github.io/hanlint/)는 같은 npm 코어로 검사, 고침,
원문 비교와 개인 기록을 제공한다. 사용 방법은
[편집기 안내](https://eddmpython.github.io/hanlint/guide.html)에서 확인한다.

다음 API는 **main과 현재 웹 편집기에 먼저 반영되어 있으며, npm 0.0.10에는 없다.**
배포 여부는 [변경 이력](https://github.com/eddmpython/hanlint/blob/main/CHANGELOG.md)에서 확인한다.

| API | 결과 |
|---|---|
| `inspectText(text, config)` | 지적, 문체 본보기, 승인 고침 후보와 지문 |
| `learnText(before, after, config)` | 사람이 확인하고 승인할 문장 고침과 표면 치환 후보 |
| `compareRevision(before, after, config)` | 자유 원고의 숫자, 링크, 코드와 H2 제목 변화 |

브라우저에서 코어를 실행하려면 사전과 모듈을 함께 조립한다.
저장소의 [정적 사이트 빌드 절차](https://github.com/eddmpython/hanlint/blob/main/skills/specs/operation/webEditor.md)를 따른다.

Python의 `hanlint learn 전.md 승인본.md --format toml`로 만든 후보는 사람이 검토한 뒤
`hanlint.toml`의 `[[patches]]`와 `[[operations]]`로 승인할 수 있다. 두 판이 같은 설정을 읽는다.
원문 일치와 문맥 조건을 통과한 고침만 제안하며, 모호한 곳에서는 기권한다.
보호할 고유명사와 프로젝트 용어는 `protectedTerms`에 넣는다.
후보 생성, 개인 승인과 공통 규칙 반영은 별도 단계다.

## 자동화와 지원 범위

GitHub Actions, pre-commit과 Claude Code 훅의 전체 설정은
[자동화 연결 안내](https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/integrations.md)에 있다.
훅은 후속 작업에 지적을 전달하며, CI의 종료 코드 검사와는 목적이 다르다.

Python 판과 공유하는 검사는 같은 사전과 적합성 자료로 검증한다.
`audit`, `map`, `diff`, `learn`, `profile`, `coverage` 등 분석·실험 명령은 Python 쪽에 있다.
전체 명령의 구분은 [명령과 설정](https://github.com/eddmpython/hanlint/blob/main/skills/specs/start/cli.md)을 참고한다.

한린트는 모든 맞춤법이나 글의 품질을 판정하지 않는다. 지적이 없어도 좋은 글이라는 보증은 아니다.
오탐과 수정 사례는 [GitHub Issues](https://github.com/eddmpython/hanlint/issues/new/choose)로 받는다.

## 라이선스

코드는 [MIT](https://github.com/eddmpython/hanlint/blob/main/LICENSE)다.
쉬운 말 자료에는 [공공누리 제1유형 고지](https://github.com/eddmpython/hanlint/blob/main/npm/koglType1.LICENSE.md)가 적용된다.
