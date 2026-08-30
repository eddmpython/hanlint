---
name: write-korean
description: 한국어 글의 요구사항이나 초안을 hanlint writingPacket으로 컴파일해 마크다운을 쓰고 고치며 사실 보존과 자연스러움을 따로 검증한다. 블로그, 보고서, 기술 문서, 안내서, 수필, 소설, 백과 초안 작성과 전면 개작, AI 같은 문체 점검, 조직이 승인한 정확 패치와 안전한 표면 치환에 쓴다.
---

# hanlint로 한국어 글 쓰기

hanlint는 글을 생성하는 모델이 아니다. 이 스킬은 요구사항과 초안을 `writingPacket`으로 컴파일한 뒤,
작문 모델이 그 계약과 근거를 사용하게 한다. 문체의 정본은 사용자의 요구다. 승인 패치는 같은 원문에
되풀이할 고침이고 유사 문장을 흉내 낼 본보기가 아니다. 승인 표면 연산은 단어 경계와 보호 원자가 맞는
한 자리에서만 이미 계산된 결과를 쓴다.
같은 종류 글의 프로파일은 비교 자료이지 따라야 할 평균이나 점수가 아니다.
`writingPacket`은 글 생성기도 품질 판정기도 아니다. 일곱 프리셋의 사실 고정 완성 글 실측에서 일반 brief를
안전하게 이기지 못했다. 공통 문형 예시는 모델이 다른 글의 수치와 문장을 결과에 옮겨 v1 패킷의 사실 표면
통과를 0/7로 낮췄으므로 v2 실행 패킷에서 빠졌다.
최종 구조화 패킷을 별도로 한 번씩 생성했을 때 사실 표면은 6/7이었지만 전체 자동 계약은 1/7뿐이었다.
guard는 위반 여섯 결과를 막는 장치이지 생성 품질 향상의 증거가 아니다.
고정 말뭉치 1,600편의 원문 없는 구조 백분위는 `rhetoricalBlueprintV1`으로 opt-in할 수 있다. 같은 일곱
brief의 짝 실측에서 길이는 후보 1/7, 기준 0/7, 사실 표면은 후보 6/7, 기준 5/7, error 0은 두 조건 모두
4/7이었다. 전체 계약은 둘 다 0/7이라 사람 선호를 재지 못했으므로 기본 전략으로 쓰지 않는다.
새 `readerTaskDraftV1` 절차를 `qwen3:8b`로 한 번씩 생성한 별도 일곱 장르 탐침에서는 사실 표면이 두
조건 모두 7/7이었고 전체 자동 계약은 일반 brief 3/7, 후보 7/7이었다. 네 건은 후보 안전 승, 세 건은
둘 다 안전이었다. 이 결과는 아래 초안 절차를 채택할 자동 안전 근거지만 자연스러움 향상 근거는 아니다.

## 결과

사용자의 사실과 목적을 보존한 한국어 마크다운 후보를 만든다. 제출할 글은 `hanlint`의 error가 0인지
확인하고, 사람이나 별도 평가자가 사실과 뜻과 유용성과 자연스러움을 따로 확인할 수 있어야 한다.

## 가장 빠른 경로

이미 초안이 있으면 다음 명령 하나로 수정 근거를 모은다.

```powershell
hanlint packet 글.md --purpose revise
```

JSON의 `contract`, `input`, `findings`, `guidance` 순서로 읽고 초안을 고친다. `comparison`은 진단 자료라
결과 글의 사실이나 문장 재료로 쓰지 않는다. 고친 뒤에는 원문과 결과의 사실을 대조하고 `hanlint 글.md`를
다시 실행한다. 이 한 바퀴가 기본이다.

## 처음부터 쓸 때

1. 사실과 수치가 있는 글은 `src/hanlint/data/writingBrief.schema.json`에 맞는 v1 `brief.json`을 먼저 만든다. `reader`,
   `task`, `preset`, 한 문장에 한 관계만 둔 `facts`, 세 필드 안의 `mustInclude`, reader·task·facts의 모든
   숫자를 천 단위 쉼표 없이 적은 `allowedNumbers`, 쓰지 않을 `forbidden`, `length`를 채운다. 정보가 없으면 사실을 추측해
   채우지 않고 사용자에게 확인할 항목으로 남긴다.
   출처가 있는 사실을 추적해야 하면 `writingBriefV2.schema.json`의 v2를 쓴다. 각 fact를 하나 이상의
   `evidence`에 연결하고 출처 URL, 고정 revision 또는 UTC 확인 시각, locator, 1,000자 이하 인용 조각과
   SHA-256, 라이선스, `unreviewed|humanVerified`를 적는다. 움직이는 `latest`, `main`, `master`, `HEAD`는
   revision으로 쓰지 않는다. `hanlint evidence brief.json`을 먼저 통과시킨다.
2. 프리셋을 고른다. 블로그 `blog`, 보고문 `report`, 기술 문서 `docs`, 단계별 안내 `guide`, 수필 `essay`,
   소설 `fiction`, 백과 `encyclopedia` 가운데 실제 결과물과 같은 것을 쓴다.
3. 구조화 brief를 draft 패킷으로 만든다.

```powershell
hanlint packet brief.json --purpose draft --output packet.json
```

   사실 계약이 필요 없는 자유 형식 글은 기존 `hanlint packet 요구.md --purpose draft --preset docs`도
   쓸 수 있다.
   절·문단·문장 예산을 시험할 때만 먼저 `hanlint blueprint brief.json`으로 사람이 읽고 다음처럼 명시적으로
   넣는다. 이 전략은 brief의 사실이나 말뭉치 문장을 늘리지 않으며 기본 패킷에는 들어가지 않는다.

```powershell
hanlint packet brief.json --purpose draft --strategy rhetoricalBlueprintV1 --output packet.json
```

근거 관계를 판정할 외부 평가기를 쓰려면 제품 원장과 섞기 전에 고정 벤치마크로 잰다.

```console
hanlint entailment cases --output entailment-cases.json
hanlint entailment evaluate predictions.json --format json
```

`cases`에 없는 gold를 프롬프트나 예측 파일에 덧붙이지 않는다. 평가기는 36개 `caseId`마다
`supported|contradicted|insufficient|abstain`과 confidence를 하나씩 낸다. 결과에서는 macro F1만 보지
말고 coverage, 선택 정확도, selective risk와 risk-coverage 곡선을 함께 읽는다. 전부 기권한 결과는 오류가
없어 보이더라도 coverage 0과 macro F1 0이다.
4. `contract.operation`과 `constraints`를 지킨다. 구조화 패킷에서는 `input.brief`만 사실 재료다. 자유 형식
   패킷에서는 `input`만 사실 재료로 쓰고 `referenceProfile`과 `comparison.current`의 수치는 결과에
   옮기지 않는다.
5. 초안을 실제 결과 파일에 쓴다. 먼저 독자가 글을 읽은 뒤 알아야 하거나 느끼거나 해야 할 한 가지를
   내부 작업 목표로 둔다. 각 원자 사실은 그 목표에 필요한 자리에서 한 번씩 쓰고, brief에 든 사실 목록을
   같은 순서로 되풀이하지 않는다. 문장 사이에 원인, 시간, 행동이나 장면이 어떻게 이어지는지 드러낸다. 도입은 독자
   질문이나 장면을 열고, 본문은 한 절에 한 가지 일을 진행하며, 마지막은 독자가 이어서 할 행동, 확인할 결과나
   달라진 장면으로 닫는다. 안내서와 기술 문서가 아니면 불필요한 점검표를 만들지 않는다. 길고 짧은 문장은
   내용에 따라 배치한다. 사용자 저장소의 글쓰기 규칙이 있으면 그것이 이 일반 절차보다 우선한다.
6. 구조화 brief와 초안을 guard로 대조한다.

```powershell
hanlint guard brief.json 글.md --format json
```

   `contractSatisfied`는 명시한 표면과 자동 error가 맞는다는 뜻뿐이다. 원자 사실의 관계와 진실, 빠진 의미,
   금지 주장의 바꿔 말하기, 독자 효용과 자연스러움은 사람이 brief와 글을 나란히 읽어 확인한다. 위반을 모델에게 통째로 자동
   재작성시키지 않는다. 빠진 사실이나 요구 밖 숫자의 정확한 자리 하나를 고치고 guard를 다시 실행한다.
7. 사실 계약을 지킨 초안에서만 수정 패킷을 만든다.

```powershell
hanlint packet 글.md --purpose revise --preset docs
```

8. `guidance`에 `patch`가 있으면 `match.sourceText`와 현재 마크다운 원문, `match.sentence`와 표식을
   걷은 현재 문장이 같은지 확인하고 그 문장 전체를
   `patch.after`로 바꾼다. 이 패치는 글쓴이가 같은 원문에 승인한 결과다. `operation`이 있으면 새 치환을
   추측하지 말고 `sourceText`가 현재 문장과 같은지 확인한 뒤 이미 계산된 `result`를 쓴다. 이는 프리셋,
   단어 경계 한 자리, 숫자·URL·식별자·경로·코드·링크와 `protectedTerms` 보존을 통과한 결과다.
   `guidance`가 비면 다른 패치나 연산을
   검색하거나 내장 본보기를 끌어오지 않는다. `findings`의 인용과 이유로 필요한 자리만 고치되,
   사실을 더하거나 뜻을 확정해야 하면 원문을 두고 사람에게 확인한다.
9. `hanlint 글.md --preset docs`를 실행한다. 확정 `fix`, 정확 패치, 안전한 표면 연산은 적용할 수 있지만,
   모델에게 전면 재작성을 자동 반복시키지 않는다. 이번 실측의 패킷 반복은 사실 표면 0/7, error 12건이었다.
   모델 수정은 한 번마다 멈춰 사실, 수치, 링크, 코드, 조건을 원문 요구사항과 대조한다. 사실을 보존한
   상태에서만 다음 error를 고친다.

## writingPacket 읽는 법

- `contract`: 작문 모델이 반드시 지킬 작업과 보존 조건이다.
- `input`: 원문, 프리셋, 감지한 문체, frontmatter다.
- 구조화 draft의 `input.brief`: 독자, 과업, 원자 사실, 보호 표면, 숫자, 금지 표면과 길이의 유일한 사실 재료다.
- v2의 `input.brief.evidence`: fact와 출처 판의 검토 가능한 연결이다. `excerpt`는 연결된 fact를 확인하는
  조각일 뿐 문체 본보기나 다른 fact의 재료가 아니다. `humanVerified`도 진실 판정이 아니다.
- opt-in `strategy`: 원문 없는 종류별 절·문단·문장 수와 도입·본문·마무리의 위치 예산이다. `reference`의
  수치, 해시와 출처 ID를 결과의 사실이나 문장 재료로 옮기지 않는다.
- `comparison.current`: 현재 글의 리듬, 어휘, 절, 문단 분포다.
- `comparison.referenceProfile`: 같은 종류의 편집 글에서 나온 백분위다. 평균 문체를 복제하지 않는다.
- `comparison.readerState`: 독자가 이미 본 화제, 수치, 생성된 파일, 아직 회수할 약속이다.
- `findings`: 결정적으로 집은 자리와 이유다.
- `guidance`: 원문을 포함한 선택 조건이 모두 맞는 승인 패치와, 유일한 단어 경계와 보호 조건을 통과해
  `result`까지 계산된 승인 표면 연산만 든다. 초안 작성 모드와 맞는 고침이 없는 수정 모드에서는 빈 배열이다.
- `verify`: 같은 설정으로 다시 확인할 명령과, error 0과 패킷이 보장하지 못하는 것의 경계다.

문형이 꼭 필요하면 현재 error 하나를 사람이 먼저 정하고 `hanlint patterns --rule <규칙>`으로 따로 본다.
공통 문형 전부를 생성 프롬프트에 넣지 않는다. 문형의 예시는 사실 재료가 아니며 그대로 옮기지 않는다.

## 승인된 고침을 다음 글에 남기기

사람이 최종본을 승인한 뒤에만 앞 초안과 승인본을 비교한다.

```powershell
hanlint learn 전.md 승인본.md --format toml
```

문장 대응과 뜻 보존을 사람이 확인한 후보만 `hanlint.toml`에 넣는다. 자동으로 전부 저장하지 않는다.
문장 전체의 의미 고침은 `[[patches]]`에 둔다. 패치에는 마크다운을 보존한 `before`, 승인한 `after`, 선택용 `sourceText`, 표식을 걷은
선택용 `sentence`, `rule`, `presets`, `cue`, `reader`가 함께 남는다.
같은 규칙과 프리셋이라도 원문이 다르면 따로 승인할 수 있다. 원문이 완전히 같은 다음 자리에서만 재생된다.

`learn`이 `[[operations]]` 후보도 냈다면 뜻이 같고 그 낱말의 다른 원문에도 적용해도 되는지 별도로
확인한다. 32자 이하의 공백, 문장부호, 한 글자 이내 표면 치환만 승인하고 지시어와 의미 재작성은 패치에
남긴다. 한국어 인명, 조직명, 제품명은 `protectedTerms`에 적는다.

## 새 작법 전략을 승격하기

잘 쓴 글 DB 검색, 새 문형, 개요 생성이나 재작성 루프를 기본 작법에 넣기 전에 같은 `brief.json`으로
`plainBrief` 기준과 후보를 각각 한 번 만든다. `writingTrial.schema.json`으로 모델, 프롬프트와 출력
SHA256을 고정하고 같은 후보 전략 trial을 `panelTrialSet.schema.json`으로 묶는다. 자체 fixture인지 외부
자료인지, 라이선스, 외부 참조 원문 포함 여부와 사람 품질 label 포함 여부를 provenance에 명시한다.

```powershell
hanlint arena panel trial-set.json --seed 42 --output suite.json
hanlint arena assign suite.json --evaluator-id reviewer-a --group targetReader --output assignment-a.json
hanlint arena review-page suite.json assignment-a.json --output review-a.html
hanlint arena assignment-record suite.json assignment-a.json review-a.json --output recorded-a.json
hanlint arena panel-adjudicate suite.json recorded-1.json recorded-2.json recorded-3.json --output adjudication.json
hanlint arena panel-reveal trial-set.json suite.json adjudication.json --output result.json
```

최소 세 평가자마다 다른 가명과 실제 역할에 맞는 group으로 `assign`과 `review-page`를 한 번씩 실행한다.
운영자는 assignment를 보관하고 평가자에게는 해당 HTML만 보낸다. 가명에 이름, 이메일이나 조직 식별자를
넣지 않는다. 평가자는 독자·과업·사실과 두 글만 보고 content를 먼저 고른다. 화면이 목소리 표본 없는
voice를 기권으로 잠그고 모든 판정과 근거가 끝났을 때만 검토 JSON을 만든다. 검토 JSON을 회수하면 해당
assignment와 함께 `assignment-record`에 넣는다. 세 평가가 모두 회수될 때까지 후보 정체성, 내부 좌우와
다른 평가자의 선택을 공개하지 않는다. 브라우저 임시 저장은 전송되지 않지만 공용 기기에서는 JSON을
내보낸 뒤 화면에서 지운다. HTML과 schema는 사람의 선택을 미리 채우거나 대신 만들지 않는다.

한쪽이 guard를 어기면 자연스러움 선호와 섞지 않고 자동 안전 결과로 끝낸다. 둘 다 충족한 경우에만
전략과 모델을 모르는 평가자 최소 세 명이 content를 먼저 확인한 뒤 자연스러움, 명료성, 독자 과업과
목소리를 각각 고른다. 다른 평가자의 선택을 보기 전에 독립 batch를 끝내고 각 선택의 구체적인 근거를
쓴다. 목소리 표본이 없으면 voice는 `cannotJudge`다. 엄격 다수뿐 아니라 차원별 Krippendorff alpha와
장르별 결과, 무승부를 0.5로 센 후보 선호 비율의 5,000회 bootstrap 구간을 함께 읽는다. 합성 품질 점수를
만들지 않는다. 최소 세 명은 사례 합의 조건일 뿐 일반화 조건이 아니다. 30개 미만 사례와 낮은 alpha에서
이겼다는 이유로 기본 작법에 전략을 넣지 않는다.

자동 심사기는 사람 batch로 넣지 않는다. 같은 suite를 두 좌우 순서로 평가하고 순서가 일치하지 않으면
기권한다.

```powershell
hanlint arena judge-cases suite.json --output judge-cases.json
hanlint arena judge-consistency suite.json judge-cases.json predictions.json
hanlint arena judge-evaluate suite.json adjudication.json judge-cases.json predictions.json
```

사람 합의 전에는 `judge-consistency`의 위치 일관성과 사용 가능 범위만 보고, 합의 뒤에만 선호 정확도,
macro F1, coverage, confusion과 calibration을 읽는다. `qwen3:8b` 일곱 쌍 탐침은 독자 과업에서 순서
일관성 0.5000, 사용 가능 범위 0.4286이었고 계약 위반 응답도 1/14였다. 이 모델을 사람 선호의 대리자로
쓰지 않는다. 현재 `rhetoricalBlueprintV1`도 일곱 쌍이 모두 자동 계약에 실패했으므로 opt-in을 유지한다.

## 하지 않을 것

- 말뭉치의 문장을 복사하거나 출처가 다른 글을 한 문체로 평준화하지 않는다.
- 청사진의 문단·문장·글자 수를 품질 점수나 반드시 맞출 정답으로 다루지 않는다. brief.length와 사실
  계약이 늘 우선이다.
- `referenceProfile`의 중앙값에 맞추려고 정상 문장을 바꾸지 않는다.
- 본보기가 있다는 이유만으로 AI 수정이 더 낫다고 주장하지 않는다. `qwen3:8b` 30쌍 실측에서는 안전한
  성공이 본보기 유무 모두 12/30이었다. 원문 완전 일치 재생은 별도 9과제에서 이유만 2/9, 일반 본보기
  3/9, 승인 패치 4/9였다. 별도 7과제의 표면 연산은 이유만 2/7, 일반 본보기 1/7, 정확 재생 2/7,
  표면 연산 4/7이었지만 통과한 표면 서명 밖으로 넓힐 근거는 아니다.
- 완성 글에서도 패킷이나 반복 수정이 자연스러움을 높였다고 주장하지 않는다. 일곱 프리셋에서 일반 brief,
  짧은 규칙, v1 패킷, 패킷 반복의 안전 승은 모두 0건이었다. 사실 표면 통과는 각각 2/7, 1/7, 0/7,
  0/7이었고 error는 2건, 4건, 7건, 12건이었다. 공통 문형을 뺀 패킷은 2/7과 error 1건으로 오염을
  없앴지만 일반 brief보다 안전하게 낫지는 않았다. 제품 v2를 다시 생성한 결과는 패킷 1/7·error 0건,
  한 번 수정 2/7·error 0건이었고 둘 다 일반 brief 대비 안전 승은 없었다. 일반 재시도, 빠진 사실 가드,
  사실 원장 재작성도 안전 승이 없었다.
- error 0을 좋은 글의 합격 판정으로 부르지 않는다.
- guard의 `contractSatisfied`를 사실 관계와 진실의 합격 판정으로 부르거나 위반 결과를 자동 재작성하지 않는다.
- evidence의 `ledgerValid`를 URL 존재, 인용 조각의 진위, fact의 함의나 진실 판정으로 부르지 않는다.
- entailment benchmark 결과를 출처나 fact의 진실, 글 품질 또는 다른 자료에서의 일반 성능으로 부르지
  않는다. 공개 KLUE 사례의 학습 오염 가능성도 남는다.
- 사람이 승인하지 않은 `learn` 후보를 `[[patches]]`나 `[[operations]]`로 저장하지 않는다.

## 되돌리기

개작이 사실이나 목소리를 잃으면 결과 파일만 이전 판으로 되돌린 뒤 `writingPacket`의 지적을 하나씩
다시 적용한다. 승인 패치가 원인이면 해당 `[[patches]]`, 표면 치환이 원인이면 해당 `[[operations]]`
항목만 빼면 즉시 재생을 멈춘다.
