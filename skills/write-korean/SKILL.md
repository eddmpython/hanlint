---
name: write-korean
description: 한국어 글의 요구사항이나 초안을 hanlint writingPacket으로 컴파일해 자연스러운 마크다운을 쓰고 고친다. 블로그, 보고서, 기술 문서, 안내서, 수필, 소설, 백과 초안 작성과 전면 개작, AI 같은 문체 제거, 조직 문체 반영에 쓴다.
---

# hanlint로 한국어 글 쓰기

hanlint는 글을 생성하는 모델이 아니다. 이 스킬은 요구사항과 초안을 `writingPacket`으로 컴파일한 뒤,
작문 모델이 그 계약과 근거를 사용하게 한다. 문체의 정본은 사용자의 요구와 승인된 프로젝트 본보기다.
같은 종류 글의 프로파일은 비교 자료이지 따라야 할 평균이나 점수가 아니다.

## 결과

사용자의 사실과 목적을 보존한 한국어 마크다운을 만든다. 완성한 글은 `hanlint`의 error가 0이고, 사람이나
별도 평가자가 사실과 뜻과 유용성을 확인할 수 있어야 한다.

## 가장 빠른 경로

이미 초안이 있으면 다음 명령 하나로 수정 근거를 모은다.

```powershell
hanlint packet 글.md --purpose revise
```

JSON의 `contract`, `findings`, `guidance`, `patterns` 순서로 읽고 초안을 고친다. 고친 뒤에는 `hanlint 글.md`를
다시 실행한다. 이 한 바퀴가 기본이다.

## 처음부터 쓸 때

1. 결과물, 독자, 독자가 하려는 일, 반드시 보존할 사실과 수치, 글의 종류를 짧은 요구사항으로 정리한다.
   정보가 없고 결과를 크게 바꾸지 않는 항목은 합리적으로 가정하고 최종 전달에서 밝힌다. 사실은 추측해
   채우지 않는다.
2. 프리셋을 고른다. 블로그 `blog`, 보고문 `report`, 기술 문서 `docs`, 단계별 안내 `guide`, 수필 `essay`,
   소설 `fiction`, 백과 `encyclopedia` 가운데 실제 결과물과 같은 것을 쓴다.
3. 요구사항이나 뼈대가 든 마크다운을 대상으로 패킷을 만든다.

```powershell
hanlint packet 요구.md --purpose draft --preset docs
```

4. `contract.operation`과 `constraints`를 지킨다. `input`의 사실을 재료로 쓰고 `referenceProfile`은 같은 종류
   글의 분포 범위를 확인하는 데만 쓴다. `patterns`의 `form`과 `example`은 문장을 세우는 틀이다.
   `instead`는 피할 꼴이다.
5. 초안을 실제 결과 파일에 쓴다. 도입에서 독자의 질문과 얻을 결과를 세우고, 본문은 한 절에 한 가지 일을
   진행하며, 마지막은 독자가 지금 할 행동이나 확인할 결과로 닫는다. 사용자 저장소의 글쓰기 규칙이 있으면
   그것이 이 일반 절차보다 우선한다.
6. 완성된 초안으로 수정 패킷을 다시 만든다.

```powershell
hanlint packet 글.md --purpose revise --preset docs
```

7. 지적이 있는 규칙만 `guidance`의 본보기로 고친다. `before` 문구를 되풀이하지 않고 `after`가 보여 주는
   변환만 본뜬다. 프로젝트 본보기가 있으면 내장 본보기보다 그 조직의 승인된 고침이 선택된다.
8. `hanlint 글.md --preset docs`를 반복해 error를 0으로 만든다. 수정하면서 사실, 수치, 링크, 코드, 조건을
   잃지 않았는지 원문 요구사항과 대조한다.

## writingPacket 읽는 법

- `contract`: 작문 모델이 반드시 지킬 작업과 보존 조건이다.
- `input`: 원문, 프리셋, 감지한 문체, frontmatter다.
- `comparison.current`: 현재 글의 리듬, 어휘, 절, 문단 분포다.
- `comparison.referenceProfile`: 같은 종류의 편집 글에서 나온 백분위다. 평균 문체를 복제하지 않는다.
- `comparison.readerState`: 독자가 이미 본 화제, 수치, 생성된 파일, 아직 회수할 약속이다.
- `findings`: 결정적으로 집은 자리와 이유다.
- `guidance`: 현재 지적과 프로젝트 문체에 필요한 전후 본보기만 든다.
- `patterns`: error 0이 검증된 문장 틀이다.
- `verify`: 같은 설정으로 다시 확인할 명령과 결과의 한계다.

## 승인된 고침을 다음 글에 남기기

사람이 최종본을 승인한 뒤에만 앞 초안과 승인본을 비교한다.

```powershell
hanlint learn 전.md 승인본.md --format toml
```

문장 대응과 뜻 보존을 사람이 확인한 후보 하나를 `hanlint.toml`의 `[[exemplars]]`에 넣는다. 자동으로 전부
저장하지 않는다. 같은 규칙과 프리셋에는 하나만 승인한다.

## 하지 않을 것

- 말뭉치의 문장을 복사하거나 출처가 다른 글을 한 문체로 평준화하지 않는다.
- `referenceProfile`의 중앙값에 맞추려고 정상 문장을 바꾸지 않는다.
- 본보기가 있다는 이유만으로 AI 수정이 더 낫다고 주장하지 않는다. lift 탐침의 실제 결과가 먼저다.
- error 0을 좋은 글의 합격 판정으로 부르지 않는다.
- 사람이 승인하지 않은 `learn` 후보를 프로젝트 본보기로 저장하지 않는다.

## 되돌리기

개작이 사실이나 목소리를 잃으면 결과 파일만 이전 판으로 되돌린 뒤 `writingPacket`의 지적을 하나씩
다시 적용한다. 프로젝트 본보기가 원인이면 그 `[[exemplars]]` 항목만 빼면 즉시 내장 본보기로 돌아간다.
