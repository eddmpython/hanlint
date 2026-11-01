---
id: start.readerContract
title: Reader Contract 프로토콜
category: start
purpose: 어떤 모델을 쓰든 같은 산문 검사 입력, 지적(Finding), 고칠 곳 하나(Patch), 검사 결과 JSON의 버전 1과 2 형식을 정한다.
whenToUse:
  - AI 산문을 타입 검사하려면 무엇을 주나
  - Contract Finding Patch가 무엇인가
  - 다른 언어나 편집기에서 hanlint 계약을 구현하려면
  - check와 verifyPatch 결과가 무엇을 보장하나
verify:
  - uv run --no-sync python -X utf8 -B -m pytest tests/guard/testContract.py tests/guard/testConformance.py tests/guard/testContractSchemas.py -q
  - node --test npm/test/contract.test.js
status: curated
---

# Reader Contract 프로토콜

hanlint가 어떤 모델에서든 똑같이 지키는 공개 계약은 `Contract`, `Finding`, `Patch` 세 개념이다. 생성 모델과 프롬프트,
편집기는 이 프로토콜 밖에 있다. 같은 UTF-8 입력, 같은 설정, 같은 버전의 규칙이면 Python과 npm이 같은
검사 결과 JSON을 낸다.

## Contract version 1

[version 1 스키마](../../../src/hanlint/data/readerContract.schema.json)는 닫힌 네 필드만 받는다.
`version`은 프로토콜 필드이고 의미 필드는 셋이다.

```json
{
  "version": 1,
  "reader": "배포를 결정할 운영자",
  "goal": "예산과 명세를 확인한다",
  "facts": [
    "예산은 380,000원이다.",
    "명세는 https://example.invalid/check 에 있다.",
    "확인 명령은 `mora check`다."
  ]
}
```

문자열은 비어 있지 않고 양끝 공백이 없는 NFC여야 한다. `facts`는 순서가 있는 비어 있지 않은 배열이며
같은 문자열을 두 번 둘 수 없다. 모르는 필드는 거부한다. Contract 해시는 키를 이름순으로 정렬하고 공백
없이 직렬화한 JSON의 UTF-8 SHA-256이다.

Contract 본문은 `reader`, `goal`, `facts`를 줄바꿈 하나로 이은 문자열이다. 여기서 지켜야 할 값(숫자, URL, 인라인 코드, 링크)의
정렬된 집합을 만든다.

- 숫자는 올바른 천 단위 쉼표를 걷고 모든 유니코드 십진 숫자를 ASCII 값으로 바꾼다. `380,000`과
  `380000`은 같은 값이다.
- `http://` 또는 `https://` URL을 잡되 닫는 괄호와 문장부호를 URL 끝에 넣지 않는다.
- 한 줄 백틱의 안쪽 문자열을 인라인 코드로 잡는다.
- 마크다운 링크의 괄호 안 목적지를 링크로 잡는다.

지켜야 할 값은 나온 횟수가 아니라 집합으로 센다. Contract에 백틱이나 링크 표식 없이 같은 값이 이미 있으면 결과 글이
그 값을 백틱이나 링크 목적지로 감싸도 새 값으로 보지 않는다. 숫자, URL, 코드, 링크를 별도 허용 목록에
다시 쓰지 않는다.

### 기존 글에서 계약 초안 만들기

이미 쓴 글은 `contract init`으로 version 1 초안을 만든다.

```console
hanlint contract init 글.md --reader "배포를 결정할 운영자" --goal "지원 버전을 확인한다"
npx hanlint contract init 글.md --reader "배포를 결정할 운영자" --goal "지원 버전을 확인한다"
```

`contractFromText(text, reader, goal)`은 지켜야 할 값을 많이 담은 원문 줄부터 늘 같은 기준으로 골라 facts 후보를
줄이고, 결과는 원문 순서로 돌려준다. 줄은 NFC로 정규화하고 양끝 공백을 걷으며 같은 줄은 처음 한 번만
남긴다. 여러 줄 링크처럼 선택한 줄에 담기지 않는 값은 정규화한 가장 짧은 글자로 보충한다. 만든 직후
원문과 비교한 지켜야 할 값의 차이는 0이다.

이 함수는 원문의 문장이 참인지 판단하거나 지켜야 할 값이 없는 의미 사실을 추측하지 않는다. 지켜야 할 값이
하나도 없으면 facts를 직접 쓰라고 알리고 멈춘다. reader나 goal이 원문에 없던 값을 추가해도 멈춘다.
기본 출력은 stdout이고 `--output`은 기존 파일을 덮지 않는다. 같은 경로를 덮으려면 `--force`가 필요하다.
초안의 facts는 자동 추출 후보이므로 사람이 사실과 빠진 의미를 확인한 뒤 check에 넣는다.

## Contract version 2

[version 2 스키마](../../../src/hanlint/data/readerContractV2.schema.json)는 의미, 자동으로 뽑은 값, 제목 구조를
서로 다른 필드로 둔다.

```json
{
  "version": 2,
  "reader": "데이터 도구를 고르는 개발자",
  "goal": "용도별 라이브러리를 비교한다",
  "facts": [],
  "surface": {
    "numbers": ["12"],
    "urls": [],
    "code": [],
    "links": []
  },
  "outline": {
    "level": 2,
    "headings": ["pandas", "Polars", "DuckDB"]
  }
}
```

`facts`는 사람이 승인한 사실만 담으며 빈 배열일 수 있다. `surface`는 원문에서 자동으로 뽑은 숫자, URL,
인라인 코드, 링크 목적지의 정렬된 집합이다. `outline`은 H1부터 H6 가운데 한 수준과 비지 않은 제목 순서를
정확히 고정한다. 제목은 NFC로 쓰고, 양끝에 공백을 두지 않으며, 같은 제목을 두 번 쓰지 않는다. 모르는 필드는 어느 객체에서도 거부한다.

```console
hanlint contract init 글.md --reader "데이터 도구를 고르는 개발자" --goal "용도별 라이브러리를 비교한다" --outline h2
npx hanlint contract init 글.md --reader "데이터 도구를 고르는 개발자" --goal "용도별 라이브러리를 비교한다" --outline h2
```

`contractFromTextV2(text, reader, goal, outlineLevel, facts)`는 원문의 지켜야 할 값과 지정한 수준의 제목을 읽는다.
원문에 없는 제목이나 사실을 추측하지 않는다. 따라서 "라이브러리마다 H2 하나"처럼 원하는 구조가 이미
정해졌다면 먼저 사람이 승인한 제목 골격을 만들거나 생성된 JSON의 outline을 검토해야 한다.

version 2 해시는 version 1과 같은 정렬 JSON, UTF-8, SHA-256 규칙을 쓴다. version 1의 필드, 해시, 결과 JSON과
고정 적합성 사례는 바꾸지 않는다.

## Finding과 check

### 초안부터 지킬 사실과 수정 범위

version 2는 선택 필드 `lockedFacts`와 `editPolicy`를 받는다. `lockedFacts`는 이미 승인한 `facts` 중에서
표현까지 그대로 유지할 문구만 고른다. 대상, 항목, 값, 단위, 기간과 부정·조건을 한 문구에 함께 적으면
숫자 집합이 같아도 관계를 뒤집은 후보를 `missingFacts`로 발견한다. 뜻을 자동으로 분석하는 기능은 아니다.
문구 밖의 모순과 다른 표현으로 쓴 같은 뜻은 이해하지 못한다. 표현을 자유롭게 바꿔야 할 사실은 고정하지 않는다.

아직 글이 없을 때도 reader와 goal, 승인 facts와 예정 outline으로 JSON을 직접 작성할 수 있다.
surface에는 사용하기로 정한 값만 둔다. 자동 추출 초안은 사실 승인이 아니므로 사람이 확인한다.
한 번 승인한 계약은 검사 지적을 없애려고 자동으로 다시 만들지 않는다.

```json
{
  "version": 2,
  "reader": "실적을 확인할 독자",
  "goal": "회사별 매출을 비교한다",
  "facts": ["A사의 매출은 100억 원이다.", "B사의 매출은 200억 원이다."],
  "surface": {"numbers": ["100", "200"], "urls": [], "code": [], "links": []},
  "outline": {"level": 2, "headings": ["실적"]},
  "lockedFacts": ["A사의 매출은 100억 원이다.", "B사의 매출은 200억 원이다."],
  "editPolicy": {"spelling": {"maxChars": 2, "maxLines": 1}}
}
```

예산의 수는 이 예시에서 선택한 정책이며 기본 기준값이 아니다. `editPolicy`가 있으면 선택한 규칙의 Finding이
가리키는 줄을 포함한 변경만 검증한다. 전후의 공통 접두·접미를 제외한 하나의 변경 창에서 Unicode 코드 포인트
수와 줄 수를 센다. 중간의 그대로인 문장도 창에 포함해 멀리 떨어진 수정의 묶음을 숨기지 못한다.
선택한 규칙의 예산이 없거나 상한을 넘으면 `newContractIssues`의 `editPolicy`로 거부한다.

`hanlint check 계약.json 글.md`는 빠진 고정 문구(`lockedFacts`)를 위반 수에 더한다. `verify-patch`는 고정 문구가 새로 빠지는 것도
거부한다. `reason: "lockedFacts"`는 누락을 복원하는 후보의 근거가 된다. editPolicy까지 선택했다면 이 근거는
규칙 Finding이 없어 자동 수정되지 않으며, 사실 복원은 원문과 출처를 사람이 확인한다.

글을 쓰는 중에는 아직 쓰지 않은 절의 제목과 사실이 빠져 있을 수 있다. 완성한 부분의 오류부터 고치고,
예정된 내용을 지우거나 계약을 느슨하게 바꾸지 않는다. 완성 후 전체 계약의 남은 의무를 확인한다.

`check(text, contract)`는 지켜야 할 값의 차이와 기존 hanlint `Finding`을 한 번 계산한다. 출력은
[checkResult 스키마](../../../src/hanlint/data/checkResult.schema.json)에 맞는다. `violationCount`는 지켜야 할 값이 달라진 것을 담는
여덟 항목의 수에 오류(`error`) Finding 수를 더한 값이다. 경고(`notice`)는 결과에 남지만 위반 수에는 더하지 않는다.

[Finding 스키마](../../../src/hanlint/data/finding.schema.json)의 필수 필드는 규칙 이름, 줄, 심각도, 범위,
문장 위치, 원문 인용, 이유다. 고칠 문장이 정해질 때만 fix나 한 곳만 바꾸는 fragment와 replacement, 순위 없는 후보를
더한다. Finding이 없다는 것은 이 버전의 규칙이 세어서 잡는 위반이 없다는 뜻이지 좋은 글이라는 판정이 아니다.

결과 JSON에는 Contract와 원문 해시가 있고 시각, 호스트, 모델 이름은 없다. 같은 입력을 다시 검사하면 같은
결과가 나온다.

version 2 결과는 [checkResultV2 스키마](../../../src/hanlint/data/checkResultV2.schema.json)에 맞는다.
기존 surface와 lint에 `outline`과 `document`를 더한다. outline은 기대 제목과 실제 제목, 위치별 어긋남을
내고 document는 문장, 문단, 절, 어절, 질문, 독자 호출 수와 잘리지 않은 절 제목을 낸다. version 2에서
`violationCount`는 지켜야 할 값이 달라진 수, 제목 위치 어긋남, 빠진 고정 문구, 오류 Finding을 더한 값이다.

CLI가 기본으로 내는 JSON은 자동화 도구가 읽는 검사 결과이고, 같은 입력이면 늘 같다. `check --format text`는 같은 결과를 결론, 근거, 다음 할 일
순서로 렌더링한다. 별도 lint와 audit을 다시 실행한 결과를 합치는 기능이 아니라 check가 한 번 만든 같은
분석표를 사람이 읽기 쉽게 보여 주는 표현이다.

text 결과는 독자가 막히는 곳을 찾는 규칙의 Finding을 `독자가 막힐 곳`으로도 묶는다. 독자가 앞에서 받은 이름, 수치, 파일과 미룬
약속만으로 지금 요구를 해결하지 못하는 곳이다. 이 묶음은 네 번째 공개 자료형이나 새 판정이 아니다. 같은 Finding을
사람이 행동 단위로 읽게 다시 묶은 것이며 JSON의 기준은 계속 `lint.items`다. 경고는 이 목록에는 보이지만
`violationCount`에는 더하지 않는다.

## Patch와 verifyPatch

[Patch 스키마](../../../src/hanlint/data/patch.schema.json)는 `reason`, `before`, `after`만 받는다.
`reason`은 check 결과에 실제로 있는 규칙 이름이나 지켜야 할 값의 차이를 담는 필드 이름이다. Patch는 자동 재작성
명령이 아니라 검증할 고침 후보 하나다.

`verifyPatch(text, patch, contract)`는 원문을 저장하지 않고 다음 사실을 확인한다.

1. `before`가 원문에 겹치지 않게 정확히 한 번 있다.
2. 바꾼 뒤 `reason`의 출현 수가 줄어든다.
3. 바꾸기 전에 없던 지켜야 할 값의 차이가 생기지 않는다.
4. 규칙 이름과 인용이 같은 오류 지적의 다중집합을 기준으로 새 오류 지적이 생기지 않는다.

version 2에서는 바꾸기 전에 없던 outline 어긋남도 3번의 계약 위반에 포함한다. `reason`으로 `outline`을
주면 기존 제목 어긋남 수가 줄어야 한다.

version 1 결과는 [patchResult 스키마](../../../src/hanlint/data/patchResult.schema.json), version 2 결과는
[patchResultV2 스키마](../../../src/hanlint/data/patchResultV2.schema.json)에 맞는다. version 2는
`newSurfaceIssues` 대신 지켜야 할 값과 outline을 함께 담는 `newContractIssues`를 쓴다. `verified`는 이 네
기계 조건을 만족했다는 사실일 뿐 의미, 진실, 자연스러움의 승인이 아니다. reason이 없는 수정은 검증되지
않는다. 따라서 공개 수정 원칙은 `Finding이 없으면 Patch도 없다`다.

## 적합성

[고정 적합성 사례](../../../src/hanlint/data/readerContractConformanceV1.json)는 규칙을 모두 끈
`surfaceOnly` 모드에서 Contract 해시, 지켜야 할 값의 보존과 차이, reason 감소, 새 값 거부, 여러 곳 거부의
전체 결과 JSON을 담는다. 다른 구현은 이 JSON을 그대로 읽어 `expected`와 구조와 값이 같은 결과를 내야 한다.
Python과 npm 테스트가 같은 배포 자료를 각각 독립 실행한다.

## WritingBrief와의 관계

`WritingBrief`와 `guard`는 생성 패킷, preset, 꼭 들어갈 글자, 쓰면 안 되는 글자, 길이, 근거 기록이 필요한 확장 계약이다.
Reader Contract는 그 기능을 없애지 않는다. 일반 편집기와 에이전트가 주고받는 가장 작은 형식만 세 의미 필드로
줄인다. 기존 brief의 `allowedNumbers`는 호환성 때문에 남아 있고 guard와 check는 지켜야 할 값을 같은 방법으로 계산해
쓴다.

## 경계와 롤백

이 프로토콜은 facts가 참인지, 서로 모순되는지, goal을 의미상 완수했는지 판정하지 않는다. 그런 검사가
필요하면 별도 평가 결과로 두고 `violationCount`에 섞지 않는다.

되돌릴 때는 공개 `check`와 `verifyPatch` 진입점과 Reader Contract 관련 스키마를 함께 제거하고 기존 `WritingBrief`와
`guard`로 돌아간다. 배포한 version 1 스키마의 필드나 뜻을 같은 버전에서 바꾸지 않는다. version 2도
배포한 뒤에는 같은 원칙을 따른다.
