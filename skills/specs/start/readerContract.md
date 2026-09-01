---
id: start.readerContract
title: Reader Contract 프로토콜
category: start
purpose: 모델에 독립적인 산문 검사 입력과 Finding, 정확 Patch, 결정적 검증 영수증의 버전 1 계약을 정한다.
whenToUse:
  - AI 산문을 타입 검사하려면 무엇을 주나
  - Contract Finding Patch가 무엇인가
  - 다른 언어나 편집기에서 hanlint 계약을 구현하려면
  - check와 verifyPatch 결과가 무엇을 보장하나
verify:
  - uv run --no-project pytest tests/guard/testContract.py tests/guard/testConformance.py tests/guard/testContractSchemas.py -q
  - node --test npm/test/contract.test.js
status: curated
---

# Reader Contract 프로토콜

hanlint의 모델 독립적 전면 계약은 `Contract`, `Finding`, `Patch` 세 개념이다. 생성 모델과 프롬프트,
편집기는 이 프로토콜 밖에 있다. 같은 UTF-8 입력, 같은 설정, 같은 규칙 판이면 Python과 npm이 같은
JSON 영수증을 낸다.

## Contract

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

Contract 본문은 `reader`, `goal`, `facts`를 줄바꿈 하나로 이은 문자열이다. 여기서 다음 보호 원자의
정렬된 집합을 컴파일한다.

- 숫자는 올바른 천 단위 쉼표를 걷고 모든 유니코드 십진 숫자를 ASCII 값으로 바꾼다. `380,000`과
  `380000`은 같은 값이다.
- `http://` 또는 `https://` URL을 잡되 닫는 괄호와 문장부호를 URL 끝에 넣지 않는다.
- 한 줄 백틱의 안쪽 문자열을 인라인 코드로 잡는다.
- 마크다운 링크의 괄호 안 목적지를 링크로 잡는다.

원자는 출현 횟수가 아니라 집합이다. Contract에 백틱이나 링크 표식 없이 같은 값이 이미 있으면 결과 글이
그 값을 백틱이나 링크 목적지로 감싸도 새 원자로 보지 않는다. 숫자, URL, 코드, 링크를 별도 허용 목록에
다시 쓰지 않는다.

## Finding과 check

`check(text, contract)`는 보호 원자 차이와 기존 hanlint `Finding`을 한 번 계산한다. 출력은
[checkResult 스키마](../../../src/hanlint/data/checkResult.schema.json)에 맞는다. `violationCount`는 여덟
보호 원자 차이의 항목 수와 error Finding 수의 합이다. notice는 영수증에 남지만 위반 수에는 더하지 않는다.

[Finding 스키마](../../../src/hanlint/data/finding.schema.json)의 필수 필드는 규칙 이름, 줄, 심각도, 범위,
지문 위치, 원문 인용, 이유다. 확정할 수 있을 때만 fix나 국소 fragment와 replacement, 순위 없는 후보를
더한다. Finding이 없다는 것은 이 규칙 판이 세어서 잡는 위반이 없다는 뜻이지 좋은 글이라는 판정이 아니다.

영수증에는 Contract와 원문 해시가 있고 시각, 호스트, 모델 이름은 없다. 같은 입력을 다시 검사하면 같은
영수증이 나온다.

## Patch와 verifyPatch

[Patch 스키마](../../../src/hanlint/data/patch.schema.json)는 `reason`, `before`, `after`만 받는다.
`reason`은 check 결과에 실제로 있는 규칙 이름이나 보호 원자 차이 필드 이름이다. Patch는 자동 재작성
명령이 아니라 검증할 후보 한 자리다.

`verifyPatch(text, patch, contract)`는 원문을 저장하지 않고 다음 사실을 확인한다.

1. `before`가 원문에 겹치지 않게 정확히 한 번 있다.
2. 바꾼 뒤 `reason`의 출현 수가 줄어든다.
3. 바꾸기 전에 없던 보호 원자 차이가 생기지 않는다.
4. 규칙 이름과 인용이 같은 error의 다중집합을 기준으로 새 error가 생기지 않는다.

결과는 [patchResult 스키마](../../../src/hanlint/data/patchResult.schema.json)에 맞는다. `verified`는 이 네
기계 조건을 만족했다는 사실일 뿐 의미, 진실, 자연스러움의 승인이 아니다. reason이 없는 수정은 검증되지
않는다. 따라서 공개 수정 원칙은 `Finding이 없으면 Patch도 없다`다.

## 적합성

[고정 적합성 사례](../../../src/hanlint/data/readerContractConformanceV1.json)는 규칙을 모두 끈
`surfaceOnly` 모드에서 Contract 해시, 보호 원자 보존과 차이, reason 감소, 새 원자 거부, 여러 자리 거부의
전체 영수증을 담는다. 다른 구현은 이 JSON을 그대로 읽어 `expected`와 구조와 값이 같은 결과를 내야 한다.
Python과 npm 테스트가 같은 배포 자료를 각각 독립 실행한다.

## WritingBrief와의 관계

`WritingBrief`와 `guard`는 생성 패킷, preset, 필수 표면, 금지 표면, 길이, 근거 원장이 필요한 확장 계약이다.
Reader Contract는 그 기능을 없애지 않는다. 일반 편집기와 에이전트의 최소 교환 표면만 세 의미 필드로
줄인다. 기존 brief의 `allowedNumbers`는 호환성 때문에 남아 있고 guard와 check는 같은 보호 원자 계산을
사용한다.

## 경계와 롤백

이 프로토콜은 facts가 참인지, 서로 모순되는지, goal을 의미상 완수했는지 판정하지 않는다. 그런 검사가
필요하면 별도 평가 결과로 두고 `violationCount`에 섞지 않는다.

되돌릴 때는 공개 `check`와 `verifyPatch` 진입점과 Reader Contract 관련 스키마를 함께 제거하고 기존 `WritingBrief`와
`guard`로 돌아간다. 배포한 version 1 스키마의 필드나 뜻을 같은 버전에서 바꾸지 않는다.
