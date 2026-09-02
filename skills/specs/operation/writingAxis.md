---
id: operation.writingAxis
title: 작문 축
category: operation
purpose: 사실 계약 (brief, guard), 근거 원장 (evidence), 작문 패킷 (packet, blueprint), 블라인드 사람 평가 (arena), 승인 고침 기억 (learn) 의 절차. 기본 작문 절차 밖에 두는 이유와 다시 들이는 조건도 여기 있다.
whenToUse:
  - brief.json 을 어떻게 만드나
  - guard 와 evidence 는 무엇을 보장하나
  - packet 은 언제 쓰나
  - 사람 평가 (arena) 를 어떻게 돌리나
  - 승인한 고침을 다음 글에 어떻게 남기나
  - 이 축이 왜 보류인가
status: curated
---

# 작문 축

hanlint 의 작문 축 넷 (arena, guard, blueprint, packet) 과 그 주변 (evidence, entailment, learn) 은 배선이 끝났고
사람 평가가 0건이다. 향상 근거의 문턱은 사람 평가 30건이다. 그 전에는 기본 작문 절차 (`skills/write-korean`) 에
넣지 않고 여기서만 절차를 든다. 실측 수는 `tests/_attempts/` 의 각 폴더 기록이 소유한다.

## 사실 계약: brief 와 guard

사실과 수치가 있는 글은 `src/hanlint/data/writingBrief.schema.json` 의 v1 `brief.json` 을 먼저 만든다. `reader`,
`task`, `preset`, 한 문장에 한 관계만 둔 `facts`, 세 필드 안의 `mustInclude`, 쓰지 않을 `forbidden`, `length` 를 채운다.
`allowedNumbers` 에는 reader 와 task 와 facts 의 모든 숫자를 천 단위 쉼표 없이 적는다. 정보가 없으면 사실을 추측해
채우지 않고 사용자에게 확인할 항목으로 남긴다.

출처가 있는 사실을 추적해야 하면 `writingBriefV2.schema.json` 의 v2 를 쓴다. 각 fact 를 하나 이상의 `evidence` 에
연결하고 출처 URL, 고정 revision 또는 UTC 확인 시각, locator, 1,000자 이하 인용 조각과 SHA-256, 라이선스,
`unreviewed|humanVerified` 를 적는다. 움직이는 `latest`, `main`, `master`, `HEAD` 는 revision 으로 쓰지 않는다.
`hanlint evidence brief.json` 을 먼저 통과시킨다. `ledgerValid` 는 URL 이 있다거나 인용 조각이 참이라거나 fact 가
함의되거나 진실이라는 판정이 아니다.

초안이 나오면 `hanlint guard brief.json 글.md --format json` 으로 brief 와 대조한다. `contractSatisfied` 는 명시한
표면과 자동 error 가 맞는다는 뜻뿐이다. 원자 사실의 관계와 진실, 빠진 의미, 금지 주장의 바꿔 말하기, 독자
효용과 자연스러움은 사람이 brief 와 글을 나란히 읽어 확인한다. 위반을 모델에게 통째로 자동 재작성시키지
않는다. 빠진 사실이나 요구 밖 숫자의 정확한 자리 하나를 고치고 guard 를 다시 돌린다.

## 작문 패킷: packet 과 blueprint

`hanlint packet brief.json --purpose draft --output packet.json` 이 구조화 brief 를 draft 패킷으로 만들고
`hanlint packet 글.md --purpose revise` 가 초안을 수정 패킷으로 만든다. `contract` 는 작문 모델이 지킬 작업과 보존
조건, `input.brief` 는 유일한 사실 재료, `comparison` 은 진단 자료 (결과의 사실이나 문장 재료로 쓰지 않는다),
`findings` 는 결정적으로 집은 자리, `guidance` 는 원문 조건이 모두 맞는 승인 패치와 계산된 표면 연산, `verify` 는
같은 설정으로 다시 확인할 명령이다. v2 실행 패킷은 공통 문형을 싣지 않는다. 문형이 필요하면 error 하나를 사람이
먼저 정하고 `hanlint patterns --rule <규칙>` 으로 따로 본다.

절과 문단과 문장 예산을 시험할 때만 `hanlint blueprint brief.json` 으로 사람이 읽고 `--strategy rhetoricalBlueprintV1`
로 명시적으로 넣는다. 청사진의 수는 품질 점수나 맞출 정답이 아니다. brief 의 length 와 사실 계약이 늘 우선이다.

패킷이나 반복 수정이 자연스러움을 높였다고 주장하지 않는다. 지금까지의 실측에서 일반 brief 를 안전하게 이긴
전략은 없다. 그 수는 `tests/_attempts/writingLift` 와 `tests/_attempts/writeFiveKinds` 의 기록에 있다.

## 사람 평가: arena

잘 쓴 글 DB 검색, 새 문형, 개요 생성이나 재작성 루프를 기본 작법에 넣기 전에 같은 `brief.json` 으로 `plainBrief`
기준과 후보를 각각 한 번 만든다. `writingTrial.schema.json` 으로 모델, 프롬프트와 출력 SHA256 을 고정하고 같은 후보
전략 trial 을 `panelTrialSet.schema.json` 으로 묶는다. provenance 에는 fixture 가 자체 것인지 외부 자료인지, 라이선스가 무엇인지, 외부에서
참조한 원문이 들어 있는지, 사람이 매긴 품질 label 이 들어 있는지를 적는다.

```powershell
hanlint arena panel trial-set.json --seed 42 --output suite.json
hanlint arena assign suite.json --evaluator-id reviewer-a --group targetReader --output assignment-a.json
hanlint arena review-page suite.json assignment-a.json --output review-a.html
hanlint arena assignment-record suite.json assignment-a.json review-a.json --output recorded-a.json
hanlint arena panel-adjudicate suite.json recorded-1.json recorded-2.json recorded-3.json --output adjudication.json
hanlint arena panel-reveal trial-set.json suite.json adjudication.json --output result.json
```

최소 세 평가자마다 다른 가명과 실제 역할에 맞는 group 으로 `assign` 과 `review-page` 를 한 번씩 실행한다. 운영자는
assignment 를 보관하고 평가자에게는 해당 HTML 만 보낸다. 가명에 이름, 이메일이나 조직 식별자를 넣지 않는다.
평가자는 독자, 과업, 사실과 두 글만 보고 content 를 먼저 고른다. 세 평가가 모두 회수될 때까지 후보 정체성, 내부
좌우와 다른 평가자의 선택을 공개하지 않는다. 한쪽이 guard 를 어기면 자연스러움 선호와 섞지 않고 자동 안전
결과로 끝낸다. 엄격 다수뿐 아니라 차원별 Krippendorff alpha 와 장르별 결과, 후보 선호 비율의 bootstrap 구간을
함께 읽는다. 합성 품질 점수를 만들지 않는다. 30개 미만 사례와 낮은 alpha 에서 이겼다는 이유로 기본 작법에
전략을 넣지 않는다.

자동 심사기는 사람 batch 로 넣지 않는다. 같은 suite 를 두 좌우 순서로 평가하고 순서가 일치하지 않으면 기권한다
(`hanlint arena judge-cases`, `judge-consistency`, `judge-evaluate`). 사람 합의 전에는 위치 일관성과 사용 가능 범위만
보고, 합의 뒤에 선호가 얼마나 맞았는지 (정확도, macro F1), 얼마나 덮었는지 (coverage), 어디서 헷갈렸는지
(confusion), 확신이 맞는지 (calibration) 를 읽는다. 지금까지 잰 로컬 모델은
사람 선호의 대리자로 쓰지 않는다.

근거 관계를 판정할 외부 평가기는 제품 원장과 섞기 전에 고정 벤치마크로 잰다. `hanlint entailment cases --output
cases.json` 과 `hanlint entailment evaluate predictions.json --format json` 이다. `cases` 에 없는 gold 를 프롬프트나
예측 파일에 덧붙이지 않는다. 결과에서는 macro F1 만 보지 말고 coverage, 선택 정확도, selective risk 와 risk-coverage
곡선을 함께 읽는다. 벤치마크 결과를 출처나 fact 의 진실, 글 품질이나 다른 자료에서의 성능으로 부르지 않는다.

## 승인한 고침을 다음 글에 남기기: learn

사람이 최종본을 승인한 뒤에만 `hanlint learn 전.md 승인본.md --format toml` 로 앞 초안과 승인본을 비교한다. 문장
대응과 뜻 보존을 사람이 확인한 후보만 `hanlint.toml` 에 넣는다. 문장 전체의 의미 고침은 `[[patches]]` 에 둔다
(`before`, `after`, 선택용 `sourceText` 와 `sentence`, `rule`, `presets`, `cue`, `reader`). 원문이 완전히 같은 다음
자리에서만 재생된다. `[[operations]]` 후보는 뜻이 같고 그 낱말의 다른 원문에도 적용해도 되는지 확인한 32자 이하의
공백, 문장부호, 한 글자 이내 표면 치환만 승인한다. 한국어 인명, 조직명, 제품명은 `protectedTerms` 에 적는다. 승인하지
않은 후보를 저장하지 않는다.

## 다시 들이는 조건

사람 평가 30건이 모이고 어느 전략이 `plainBrief` 를 자동 안전과 사람 선호 둘 다에서 이기면, 그 전략만
`skills/write-korean` 의 다섯 단계 가운데 한 자리에 넣는다. 그 전에는 이 문서가 절차의 유일한 자리다.

## 되돌리기

개작이 사실이나 목소리를 잃으면 결과 파일만 이전 판으로 되돌린 뒤 지적을 하나씩 다시 적용한다. 승인 패치가
원인이면 해당 `[[patches]]`, 표면 치환이 원인이면 해당 `[[operations]]` 항목만 빼면 즉시 재생을 멈춘다.
