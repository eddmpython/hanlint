# hanlint

[![PyPI](https://img.shields.io/pypi/v/hanlint?label=pypi)](https://pypi.org/project/hanlint/)
[![npm](https://img.shields.io/npm/v/hanlint?label=npm)](https://www.npmjs.com/package/hanlint)
[![CI](https://github.com/eddmpython/hanlint/actions/workflows/ci.yml/badge.svg)](https://github.com/eddmpython/hanlint/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/hanlint)](https://pypi.org/project/hanlint/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**한국어 글쓰기 검사 도구 (Korean prose linter).** 마크다운 원고에서 번역투, 명사 나열, 이중 피동,
가리킬 것 없는 지시어, 조각난 문단처럼 **세면 확정되는 결함**을 찾아 자리와 이유와 다시 쓴 본보기를 준다.
맞춤법 검사기가 아니다. 맞춤법이 맞는데도 안 읽히는 글을 잡는 문장과 문단의 린터다.

파이썬과 npm 두 판이고 런타임 의존성이 없다. 블로그 원고, 기술 문서, 보고서, AI 가 쓴 초안을 발행 전에
게이트로 막는 자리에 쓴다.

```powershell
pip install hanlint      # 파이썬이 없으면 npx hanlint 글.md
hanlint 글.md
```

## 읽기 쉬운 글이란 무엇인가

읽기 쉬운 글은 쉬운 내용을 다룬 글이 아니다. **독자가 문장을 머릿속에서 다시 번역하지 않아도 되는 글**이다.
어려운 내용도 그렇게 쓸 수 있고, 쉬운 내용도 그렇게 못 쓸 수 있다.

독자가 다시 번역하게 만드는 자리는 정해져 있다. 아래 왼쪽을 읽으면 뇌가 한 번 멈춘다.

| 독자가 멈추는 문장 | 바로 읽히는 문장 |
|---|---|
| 가상환경 생성 후 패키지 설치 확인 절차를 따릅니다 | 가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다 |
| 이 기능을 통해 파일 생성이 가능합니다 | `저장` 버튼을 누르면 `report.csv` 가 만들어집니다 |
| 결과가 저장되어집니다 | 결과가 저장됩니다 |
| 표를 엽니다. 이것을 고칩니다 | 표를 엽니다. `금액` 열의 값을 고칩니다 |
| 병합 셀은 첫 칸에만 값이 있습니다. 나머지는 빈값입니다. 정렬하면 순서가 깨집니다 | 병합 셀은 첫 칸에만 값이 들어 있고 나머지는 비어 있습니다. 그대로 정렬하면 빈 칸이 값과 떨어져 순서가 깨집니다 |

왼쪽이 나쁜 까닭은 취향이 아니다. 각각 **독자에게 일을 떠넘긴다.** 첫째는 조사를 끼워 넣게 하고, 둘째는
무엇을 눌러 무엇이 생기는지 짐작하게 하고, 셋째는 같은 뜻을 두 겹으로 읽게 하고, 넷째는 스크롤을 되돌리게
하고, 다섯째는 세 문장 사이의 관계를 독자가 직접 세우게 한다.

이 다섯 가지에는 공통점이 하나 더 있다. **전부 세어서 확정된다.** 명사가 몇 개 이어졌는지, 피동이 몇 겹인지,
지시어가 가리킬 것이 앞 문장에 있는지, 문단에 인과 표지가 하나라도 있는지는 읽지 않고도 셀 수 있다.

hanlint 는 그 셀 수 있는 것만 맡는다. 재미있는지, 설득력이 있는지, 검색해 들어온 독자가 원하던 답을
받았는지는 판정하지 않는다. 그것은 사람과 LLM 평가자가 더 잘한다. 그래서 맞춤법 검사기와도 겹치지
않는다. 맞춤법 검사기는 낱말이 틀렸는지 보고 hanlint 는 문장과 문단이 독자에게 일을 떠넘기는지 본다.

## hanlint 가 한국어 글에서 잡는 것

지적마다 **자리, 이유, 그리고 이렇게 쓴다는 본보기**를 준다. 세 번째가 이 도구의 핵심이다.

```text
설정: 기본값

글.md  집은 자리 2

글.md:1  [doublePassive]
  결과가 저장되어집니다.
  `되어지` 는 피동에 어지다 를 또 붙인 이중 피동이다. 하나만 남긴다
  고친 뒤: 결과가 저장됩니다.

글.md:3  [nounPile]
  가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
  명사 6개가 조사 없이 이어진다. 관계가 표시되지 않아 독자가 조사를 끼워 넣는다. 동사로 되돌린다

본보기 (고치기 전, 고친 뒤)
  [doublePassive]
    전  결과가 저장되어집니다.
    후  결과가 저장됩니다.
  [nounPile]
    전  가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
    후  가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다.

다음: error 2건 가운데 1건은 hanlint fix 가 바로 고친다. 나머지는 손으로 고친다
```

**왜 본보기인가.** 실제 발행된 글 다섯 편에 돌려 재 봤다. 지적 104건 가운데 기계가 자동으로 고칠 수 있는
것은 0건이었다. 나머지 100%는 "무엇이 틀렸다"만 듣고 "그럼 어떻게 쓰나"는 글쓴이가 알아서 해야 했다.
금지 목록은 사람을 고치게 만들지 못한다. 그래서 규칙마다 실제로 검증된 전후 짝을 달았고, 지금은
그 104건 전부에 본보기가 붙는다. 재는 방법과 숫자는 [tests/_attempts/fixReach/](tests/_attempts/fixReach/)
에 있다.

본보기는 장식이 아니라 **검증된 데이터**다. `before` 는 그 규칙에 실제로 잡히는 글이고 `after` 는 같은 뜻인데
안 잡히는 글이며, 게이트가 매번 둘 다 돌려 확인한다. 안내가 틀리면 나쁜 글이 퍼지기 때문이다.

### 본보기가 그 글의 말투를 따른다

규칙마다 둔 기본 본보기 54개와 문형 10개는 데이터에 합니다체 한 벌만 둔다. lint 와 watch 가 글의 종결을 세어 합니다체,
한다체, 해요체 가운데 하나로 바꿔 보여 준다. 한다체 명세에 `확인합니다` 라고 남의 말투로 고치라고 하지
않는다. `hanlint explain <규칙> --register 한다` 와 `hanlint patterns --register 해요` 로 문체를 직접
고를 수도 있다.

같은 결함도 글의 종류에 따라 풀어 쓰는 법이 다르면 문맥 본보기를 고른다. 지금 `nounPile` 은 기본 절차문,
보고서, 기술 문서와 백과에 서로 다른 짝을 두어 모두 56개다. `--preset report` 로 검사한 보고서에는 사업
이름의 관계를 푼 짝이 나오고, `--preset docs` 에는 기술 용어를 남긴 채 실패 조건과 행동을 푼 짝이 나온다.
어느 짝이든 고치기 전은 잡히고 고친 뒤는 모든 error 가 0인지 세 문체에서 게이트가 확인한다.

### 승인 고침의 정확 재생

`hanlint learn 전.md 후.md` 는 글쓴이가 실제로 고쳐서 지적이 사라진 문장 짝과 그때의 국소 표지와 독자
상태를 후보로 낸다. 여러 문장을 한꺼번에 다시 쓴 모호한 구간은 추측하지 않는다. 출력은 제안일 뿐이며,
사람이 문장 대응과 뜻 보존을 확인한 것만 `hanlint.toml` 의 `[[patches]]` 에 승인한다.

```console
hanlint learn 전.md 후.md
hanlint learn 전.md 후.md --format toml
```

승인 패치는 유사도 검색을 하지 않는다. NFC로 조합하고 줄과 연속 공백만 눕힌 마크다운 원문 `sourceText`,
표식을 걷은 `sentence`, 규칙, 프리셋, 국소 표지, 문장 직전 독자 상태가 모두 같고 패치가 하나일 때만
승인한 `after`를 그대로 돌려준다. 같은 규칙과
표지라도 원문이 한 글자 다르면 기권한다. 그래서 같은 규칙 아래 서로 다른 승인 원문을 여러 개 쌓을 수
있지만, 비슷한 문장에 남의 이름과 수치와 사실을 옮기지는 않는다. `before`, `after`, `sourceText`는 인라인
코드와 링크 같은 마크다운을 보존하고, `sentence`는 그 표식만 걷은 선택용 원문이다.

### 승인 고침의 안전한 표면 전이

`learn`은 정확 패치와 별도로 공백, 문장부호, 한 글자 이내의 작은 표면 치환도 후보로 낸다. 사람이 뜻이
같고 다른 원문에도 적용해도 된다고 확인한 후보만 `[[operations]]`로 승인한다.

```toml
protectedTerms = ["한린트", "김민지"]

[[operations]]
before = "여러가지"
after = "여러 가지"
presets = ["blog"]
```

연산은 유사도 검색이나 규칙 이름으로 선택하지 않는다. 승인 전후에서 추출한 조각이 32자 이하이고, 공백과
문장부호를 걷은 편집 거리가 1 이하이며, 현재 문장의 단어 경계 한 자리에만 정확히 나타날 때만 `result`를
낸다. 숫자, URL, 라틴 식별자, 파일 경로, 인라인 코드, 링크 목적지는 자동으로 보존한다. 한국어 고유명사는
표층만으로 알아낼 수 없으므로 `protectedTerms`에 명시해 잠근다. 지시어와 의미 재작성, 여러 자리 일치,
기존 확정 fix나 원문 완전 일치 패치와 겹치는 문장은 기권한다.

### AI에 작문 근거를 한 번에 건넨다

`hanlint packet 글.md`는 원문, 현재 지문, 독자 상태, 같은 종류의 편집 글 분포, 실제 지적, 정확히 선택된
승인 패치와 안전하게 실행한 표면 치환을 `hanlint.writingPacket` JSON 하나로 묶는다. 생성 모델이 바뀌어도 근거는 같다. 처음부터
쓸 때는 `--purpose draft`, 초안을 고칠 때는 `--purpose revise`를 쓴다. 말뭉치 문장을 검색해 복사하지 않고
분포와 전후 변환만 전달하므로 공통 AI 문체로 평준화하는 위험도 줄인다.

```console
hanlint packet 요구.md --purpose draft --preset docs
hanlint packet 초안.md --purpose revise --output packet.json
```

사실과 수치가 중요한 새 글은 자유 형식 요구 대신 [writing brief 스키마](src/hanlint/data/writingBrief.schema.json)를
쓴다. 원자 사실의 `id`는 대조용이고 글에는 나오지 않는다. `allowedNumbers`에는 reader, task, facts에
있는 숫자를 천 단위 쉼표 없이 모두 적는다.

```json
{
  "version": 1,
  "preset": "docs",
  "reader": "처음 쓰는 작성자",
  "task": "명령을 실행하고 종료 코드를 해석한다",
  "facts": [
    { "id": "F1", "statement": "명령은 `mora check`이고 종료 코드는 0이다." }
  ],
  "mustInclude": ["`mora check`", "종료 코드는 0"],
  "allowedNumbers": ["0"],
  "forbidden": ["자동으로 고친다"],
  "length": { "min": 100, "max": 300 }
}
```

```console
hanlint packet brief.json --purpose draft --output packet.json
hanlint guard brief.json 초안.md
```

구조화 draft 패킷에는 `comparison`이 없다. brief만 사실 재료로 전달한다. `guard`는 빠진 필수 표면,
요구 밖 숫자·URL·코드·링크 목적지, 금지 표면, 마크다운 원문의 글자 수와 hanlint error를 보고하고 글을 바꾸지 않는다.
종료 코드 0은 이 표면 계약을 충족했다는 뜻이고 1은 위반이 있다는 뜻이다. 사실 관계와 진실, 빠진 의미,
금지 주장의 바꿔 말하기, 독자 효용과 자연스러움은 여전히 사람이나 별도 평가가 확인한다.
최종 구조화 패킷으로 일곱 종류를 한 번씩 생성한 탐침에서는 사실 표면 6/7, 길이 1/7, error 0은 3/7,
전체 자동 계약은 1/7이었다. guard는 나머지 여섯 결과를 막았지만 생성 품질 향상을 입증하지는 않았다.

출처가 있는 사실은 기존 v1 대신 [근거 원장 brief v2](src/hanlint/data/writingBriefV2.schema.json)를 쓸 수
있다. facts의 모양은 그대로 두고 `evidence`가 각 fact ID를 고정 출처 판과 짧은 인용 조각에 연결한다.
각 기록은 `E1` ID, `factIds`, 사용자 정보가 없는 HTTP(S) `sourceUrl`, 고정 `revision` 또는 UTC
`checkedAt`, `locator`, 1,000자 이하 `excerpt`와 그 SHA-256, `license`, `reviewStatus`를 갖는다.

```console
hanlint evidence brief-v2.json
hanlint evidence brief-v2.json --format json
hanlint packet brief-v2.json --purpose draft --output packet.json
```

`evidence`는 근거 없는 fact, 없는 fact를 가리키는 기록, 움직이는 revision, 조각 변조, 라이선스 누락을
결정적으로 거부한다. `humanVerified`는 사람이 그 연결을 검토했다는 상태일 뿐이다. URL이 실제로 열리는지,
조각이 진짜인지, 조각이 fact를 함의하는지와 fact가 참인지는 판정하지 않는다. v2 draft 패킷에서도
`facts.statement`만 주장 재료이며 excerpt의 다른 이름·수치·문장을 결과로 확산하지 않는다. 기존 v1
schema, 로딩, guard와 기본 draft packet 해시는 그대로다.

근거 조각과 fact의 문맥상 관계를 판정하는 외부 평가기는 별도 벤치마크로 잰다. 배포 평가판은
[KLUE-NLI](https://github.com/KLUE-benchmark/KLUE) v1.1 dev의 여섯 source에서 세 관계를 두 개씩 고른
36개다. 각 사례는 작성자 한 표와 독립 검토자 네 표 가운데 4표 이상이 gold와 일치한다. GUID 해시 순으로
선택해 손으로 유리한 사례를 고르지 않았고 전제와 가설 중복을 막았다.

```console
hanlint entailment cases --output entailment-cases.json
hanlint entailment evaluate predictions.json
hanlint entailment evaluate predictions.json --format json
```

`cases`는 gold와 다섯 표를 빼고 `caseId`, domain, evidence excerpt와 atomic fact만 낸다. 외부 평가기는
[예측 schema](src/hanlint/data/entailmentPredictions.schema.json)에 맞춰 `supported`, `contradicted`,
`insufficient`, `abstain`과 0부터 1까지 confidence를 사례마다 하나씩 기록한다. `evaluate`는 class별
혼동행렬과 F1, macro F1, coverage, 기권을 뺀 선택 정확도, selective risk와 risk-coverage 곡선을 낸다.
기권만 늘려 오류를 감춘 결과는 coverage와 macro F1에서 함께 드러난다.
Python에서는 `entailmentCases()`와 `evaluateEntailment(predictions)`가 같은 계약과 결과를 낸다.

이 평가는 문장 두 개의 관계만 잰다. 원문 자체나 fact가 세상에서 참인지 판정하지 않으며, 36개 공개 KLUE
사례가 모델 학습에 들어갔을 가능성도 배제하지 못한다. 따라서 한 모델 결과를 일반 함의 성능이나 글 품질
향상으로 부르지 않는다. 한국어 문장과 주석이 든
[`evidenceEntailmentV1.json`](src/hanlint/data/evidenceEntailmentV1.json)은 CC BY-SA 4.0이고, 코드와 다른
데이터의 MIT 라이선스와 [분리해 표시한다](src/hanlint/data/evidenceEntailmentV1.LICENSE.md).

구조가 필요하면 고정 말뭉치 1,600편의 종류별 절·문단·문장·글자 수 백분위로 원문 없는 청사진을 만든다.
배포 데이터에는 원문, 제목, URL과 문장이 없고 허가된 출처 ID, 고정 판의 해시와 숫자 분포만 있다.
`blueprint`은 마크다운 절 수와 도입·본문·마무리의 위치별 글자·문단·문장 예산을 따로 내며 사실이나
표현을 공급하지 않는다.

```console
hanlint blueprint brief.json
hanlint blueprint brief.json --format json --output blueprint.json
hanlint packet brief.json --purpose draft --strategy rhetoricalBlueprintV1 --output packet.json
```

`--strategy`는 구조화 brief에서만 쓰는 opt-in이다. 기본 draft 패킷은 바뀌지 않는다. `qwen3:8b`로 같은
일곱 brief를 한 번씩 짝 생성한 결과, 청사진 후보는 길이를 1/7에서 지켰고 기준은 0/7이었다. 사실 표면은
후보 6/7, 기준 5/7, error 0은 두 조건 모두 4/7이었다. 전체 자동 계약은 두 조건 모두 0/7이라 일곱 쌍
모두 블라인드 선호 평가 전에 막혔다. 따라서 이 전략은 구조 실험 도구이지 자연스러움 향상이 입증된
기본 작법이 아니다.

새 작법 전략이나 잘 쓴 글 DB 검색은 [writing trial 스키마](src/hanlint/data/writingTrial.schema.json)로 일반
`plainBrief` 결과와 후보 결과를 같은 brief에 묶어 검증한다. 여러 장르를
[`panelTrialSet`](src/hanlint/data/panelTrialSet.schema.json)으로 묶을 때 자료의 출처 성격, 라이선스,
외부 참조 원문과 사람 품질 label 포함 여부까지 해시로 고정한다. 모델, 프롬프트와 출력 SHA256을 고정한
뒤 사람 패널과 자동 심사기를 분리한다.

```console
hanlint arena panel trial-set.json --seed 42 --output suite.json
hanlint arena assign suite.json --evaluator-id reviewer-a --group targetReader --output assignment-a.json
hanlint arena review-page suite.json assignment-a.json --output review-a.html
hanlint arena assignment-record suite.json assignment-a.json review-a.json --output recorded-a.json
hanlint arena panel-adjudicate suite.json recorded-1.json recorded-2.json recorded-3.json --output adjudication.json
hanlint arena panel-reveal trial-set.json suite.json adjudication.json --output result.json
hanlint arena judge-cases suite.json --output judge-cases.json
hanlint arena judge-consistency suite.json judge-cases.json predictions.json
hanlint arena judge-evaluate suite.json adjudication.json judge-cases.json predictions.json
```

`panel`은 두 결과를 먼저 guard로 검사한다. 한쪽만 자동 계약을 충족하면 안전 결과만 기록하고 본문 비교를
내지 않는다. 둘 다 충족할 때만 전략명, 모델명과 작성자를 숨기고 독자, 과업, 원자 사실과 제약을 함께
보인다. 평가자는 좌우 content를 먼저 확인하고 자연스러움, 명료성, 독자 과업과 목소리를 따로 고른다.
목소리 표본이 없으면 기권한다. 최소 세 명의 독립 batch에서 엄격 다수, 차원별 Krippendorff alpha,
장르별 결과와 5,000회 bootstrap 구간을 낸다. 합성 품질 점수는 없다.

`assign`은 평가자 가명과 suite 해시에서 사례별 좌우를 고정하되 어느 쪽을 바꿨는지 적지 않는다.
운영자는 `assignment.json`을 검증 입력으로 삼아 `review.html`을 만들고 평가자에게는 HTML만 보낸다.
HTML은 외부 스크립트와 네트워크 요청이 없는 단일 파일이다. 입력은 평가자가 연 브라우저에만 임시 저장되고,
content를 끝내기 전에는 선호를 고를 수 없으며 목소리 표본이 없으면 voice가 `cannotJudge`로 잠긴다.
평가자는 모든 판정과 근거를 채워 `review.json`을 저장한다. 이름이나 이메일 대신 연구 안에서만 쓰는 가명을
사용하고 공용 기기에서는 내보낸 뒤 화면의 임시 저장 지우기를 누른다. 운영자는 `assignment-record`로
배정 해시와 누락·변조를 검사하고 좌우를 원래 suite 방향으로 되돌린다. 세 평가가 모두 회수되기 전에는
서로의 JSON이나 후보 정체성을 공개하지 않는다. [내보내기 schema](src/hanlint/data/panelAssignmentReview.schema.json)는
파일 형식만 확인하며 사람의 판단을 대신 만들지 않는다.

자동 심사기는 같은 쌍을 두 좌우 순서로 받고, 선택이 일치하지 않으면 기권한다. 사람 합의가 없을 때는
위치 일관성과 사용 가능 범위만 계산한다. 합의가 생긴 뒤에만 정확도, macro F1, coverage, confusion,
Brier와 calibration을 낸다. 일곱 쌍 `qwen3:8b` 실제 탐침에서 독자 과업의 순서 일관성은 0.5000,
사용 가능 범위는 0.4286이었고 14개 응답 중 1개는 content 실패 뒤에도 선호를 내 계약에서 거부됐다.
따라서 LLM 평가는 사람 선호나 진실로 합치지 않는다. 최소 세 명은 합의 계산 조건일 뿐 일반화 조건이
아니며 30개 미만 사례와 낮은 alpha는 탐색 결과로만 보고한다.

`readerTaskDraftV1` 절차도 같은 일곱 장르에서 실제로 한 번씩 생성했다. 사실 표면은 기준과 후보 모두
7/7이었고 전체 자동 계약은 기준 3/7, 후보 7/7이었다. 후보 안전 승 네 쌍과 둘 다 안전 세 쌍을 얻었지만,
사람 패널은 아직 없으므로 자연스러움 향상으로 부르지 않는다. 재현 절차와 해시는
[`writingArena` 탐침 기록](tests/_attempts/writingArena/probeWritingArena_log.md)에 있다. 조사 근거와 자료
사용 경계는 [`writingArena v1 조사`](tests/_attempts/writingArena/writingArenaV1_research.md)에 정리했다.

기존 `arena blind`, `record`, `reveal`, `aggregate` 단일 평가 흐름도 호환하려고 남겨 두었다. 새 전략을
승격할 때는 독자와 사실 맥락, 다중 사람 합의와 위치 편향 측정이 있는 panel 흐름을 쓴다.

실행 절차는 [write-korean 스킬](skills/write-korean/SKILL.md)에 있다. 원문 전문을 JSON에 넣지 않으려면
`--no-source`를 붙인다.

패킷은 자연스러운 글을 보장하는 생성기가 아니다. 일곱 프리셋의 사실 고정 완성 글 실측에서 일반 brief의
사실 표면 통과는 2/7이었고, 모든 공통 문형 예시를 넣은 v1 패킷은 0/7이었다. 모델이 문형 예시와 비교
수치를 결과의 사실로 복제했기 때문이다. 공통 문형을 제거한 실제 v2 패킷은 1/7과 error 0건, v2로 한 번
수정한 결과는 2/7과 error 0건이었다. v1의 error 7건과 반복 수정 12건은 없앴지만 일반 brief를 안전하게
이긴 과제는 없었다. 그래서 v2 실행 패킷에는 공통 `patterns`를 싣지 않는다.
문형이 필요하면 실제 error 하나를 확인한 사람이 `hanlint patterns --rule <규칙>`으로 따로 읽는다.
`comparison`은 진단 자료일 뿐 결과 글의 사실이나 문장 재료가 아니다. 사실, 뜻, 독자 과업과 자연스러움은
원문 대조와 별도 평가가 맡는다.

이 변환은 형태소 분석기를 넣지 않은 작은 형태 층이 맡는다. 조사 맞추기, 종결 어미의 어간과 시제와 서법,
피동과 사동을 따로 다룬다. 기준 말뭉치 390편, 17,420문장에서 합니다체 1,992개는 전부, 한다체 12,255개는
12,209개를 원문 그대로 다시 만들었다. 그렇게 확인한 활용형 14,201개는 세 문체를 모두 만든다. 해요체
원문을 거꾸로 푸는 일은 표층만으로 확정되지 않아 범위에 넣지 않았다.

### 고를 수 있을 만큼만 후보를 낸다

`--format json` 의 지적에는 만들 수 있을 때만 `candidates` 가 붙는다. 각 후보는 문장 `text` 와 왜 만든
것인지 적은 `why` 를 가진다. 기계는 뜻이 필요한 다음 두 종류를 고르지 않는다.

- 긴 문장을 끊어 볼 연결 어미 뒤
- 지시어가 가리킬 수 있는 앞 문장의 명사

범위는 말뭉치에서 재고 사람이 실제 문맥을 읽어 골랐다. 후보를 시험한 지적은 1,498건이고 규칙마다 10건씩
50건을 검토했다. 장문과 지시어 후보는 각각 10건 중 7건을 골랐다. 명사 나열은 1건, 종결 어미 반복은
0건이라 제품에서 뺐다. 이중 피동은 10건 전부를 골랐다. 추가 말뭉치의 표층 일치 58건 가운데 직접 인용
1건은 글쓴이의 사용이 아니라 지적에서 제외했고, 남은 57건은 모두 확정 치환으로 승격했다.
다섯 종류의 새 글을 쓴 3회차에서는 첫 검사 error 14, notice 6에 후보 14개가 나왔고, 두 번 고친 뒤 다섯 편
모두 error 0, notice 0이었다.

## 설치와 첫 검사, 30초

```powershell
pip install hanlint
hanlint
```

인자 없이 치면 첫 화면이 나온다. 지금 이 폴더에 있는 마크다운 이름으로 만든 예시가 거기 있다.

```text
hanlint 0.0.7  한국어 글에서 세면 확정되는 결함을 집는다. 좋은 글인지는 판정하지 않는다

  hanlint 초안.md        검사한다. 자리와 이유와 고칠 말이 나온다
  hanlint fix 초안.md    기계가 확실히 고칠 수 있는 자리를 원문에 적용한다
  hanlint audit 초안.md  글의 모양을 지도와 분포로 본다

이 폴더의 마크다운: 초안.md. 폴더를 통째로 줘도 된다 (hanlint .)
```

그다음은 셋만 알면 된다.

| 하고 싶은 것 | 치는 것 |
|---|---|
| 이 글에 무엇이 잘못됐나 | `hanlint 글.md` |
| 기계가 고칠 수 있는 것은 먼저 고쳐 줘 | `hanlint fix 글.md` |
| 쓰는 동안 계속 봐 줘 | `hanlint watch 글.md` |

`npx hanlint 글.md` 는 설치 없이 같은 검사를 한다. 폴더를 주면 그 아래 마크다운을 찾되 점으로 시작하는
폴더와 `node_modules` 에는 안 들어간다. 그 안을 보려면 그 폴더를 직접 준다.

## 글의 종류를 고른다: 블로그, 보고서, 문서, 안내서, 수필, 소설, 백과

기본은 블로그다. 독자를 부르고 절마다 눈에 보이는 결과를 남기는 글이 기준이라, 보고서나 참고 문서에
그대로 대면 맞지 않는 지적이 나온다. 그때는 규칙을 하나씩 끄지 말고 종류를 고른다.

```powershell
hanlint 명세.md --preset docs      # 이번 검사에만
hanlint init --preset docs         # 저장소에 고정할 때
```

| 프리셋 | 누구를 위한 것 | 끄는 규칙 | 견주는 프로파일 |
|---|---|---:|---|
| `blog` | 독자를 부르고 절마다 결과를 남기는 글 | 0개 | 블로그 |
| `guide` | 단계별 안내서 | 0개 | 안내서 |
| `report` | 보고서 | 6개 | 보고문 |
| `essay` | 수필 | 6개 | 수필 |
| `fiction` | 소설 | 6개 | 소설 |
| `docs` | 참고 문서, 명세, README | 8개 | 기술 문서 |
| `encyclopedia` | 백과 항목 | 8개 | 백과 |

어느 규칙이 꺼지는지는 여기 옮겨 적지 않는다. `hanlint rules --preset docs` 가 지금 도는 목록에
꺼진 것을 표시해 보여 준다.

`--preset` 은 설정 파일 없이 이번 실행에만 정한다. 남의 저장소에 파일을 만들지 않고 문서 한 편을
검사할 때 쓴다. 한 폴더에 종류가 섞여 있으면 종류마다 나눠 돌린다. 지금 무엇이 켜져 있는지는
`hanlint doctor` 가 한 화면으로 답한다.

### 같은 종류의 편집된 글과 견준다

프리셋은 규칙만 고르지 않는다. 블로그, 보고문, 기술 문서, 단계별 안내, 수필, 소설, 백과의 기준
프로파일도 고른다. 프로파일은 재사용 조건과 판본을 고정한 글 1,600편, 문장 144,214개에서 문장 길이,
쉼표 수, 새 화제 수, 유보 표현 수의 분포를 센 작은 표다. 원문은 제품에 싣지 않는다.

`outsideProfile` 은 그 종류 문장의 99% 밖에 있는 자리만 notice 로 낸다. "문장 길이 47어절, 보고문
3,897문장 가운데 상위 0.8%"처럼 관찰한 사실을 말할 뿐 고치라고 명령하거나 글을 채점하지 않는다.
프리셋이 틀리면 대조도 틀리므로 종류가 섞인 폴더는 나눠 돌린다. 조직에서 승인한 글의 문체가 더 중요한
때는 그 글들로 프로파일을 바꾼다.

```powershell
hanlint profile build 승인된글들/ --output 우리문체.json
hanlint 새글.md --profile 우리문체.json
```

### 한국어 학습자에게 처음 풀어 쓸 낱말을 찾는다

한국어 학습자가 독자라면 파이썬 판의 `terms` 를 한 번 더 돌린다. 국립국어원의 한국어 학습용 어휘
5,965개를 A, B, C로 나눈 원 자료와 화제어의 첫 등장을 맞댄다.

```powershell
hanlint terms 글.md
hanlint terms 글.md --outside --format json
```

기본 출력은 여러 뜻이 모두 C에 속하는 화제어만 보인다. A/C처럼 동형어의 등급이 갈리면 C라고 단정하지
않는다. `--outside` 는 목록 밖 한글 화제어도 내지만 최신 전문어와 고유명사를 가르지 못하므로 후보일
뿐이다. 이 등급은 한국어 학습자를 위한 것이며 한국어 모어 화자의 낱말 난도나 글의 품질 점수가 아니다.
자료원, 필드, 인코딩, 라이선스, 한계는
[`learningVocabularySource.toml`](src/hanlint/data/learningVocabularySource.toml)이 소유한다.

## 이미 쓴 글이 많은 저장소에 들일 때

새 도구를 이미 쌓인 문서에 대면 첫날 지적이 쏟아진다. 실측이다. 남의 저장소 문서 여섯 편에 그냥 돌리면
error 가 21건 나왔다. 규칙이 틀려서가 아니라 그 글들이 실제로 문단이 조각나 있고 제목이 문장이기
때문이다. 그런데 첫날 21건을 보는 팀은 도구를 끈다.

그래서 **지금 있는 것을 잠그고 새로 생긴 것만 막는다.**

```powershell
hanlint baseline 글들/          # .hanlint-baseline.json 을 만들어 커밋한다
hanlint 글들/ --baseline        # 그다음부터 새로 생긴 지적만 나온다
```

잠금은 줄 번호가 아니라 **인용문**으로 건다. 코드 린터는 파일과 줄로 잠그지만 글은 문단 하나만 고쳐도
아래 줄 번호가 전부 밀려 잠근 것이 풀린다. hanlint 는 지적이 인용문을 들고 있어서 글자로 잠글 수 있고,
그래서 성질 하나가 따라온다.

| 글에 한 일 | 잠금이 하는 일 |
|---|---|
| 문단을 옮겨 줄 번호가 밀렸다 | 그대로 잠겨 있다. 헛경보가 안 난다 |
| 잠긴 문장을 고쳤다 | 새 지적이 된다. 손댔으면 책임진다 |
| 문장을 지웠다 | `hanlint baseline 글들/ --prune` 이 죽은 잠금을 치운다 |
| 새 문장을 썼다 | 잠금과 무관하게 잡힌다 |

**손댄 자리만 막는다.** 기한도 비율도 정하지 않아도 글을 고칠 때마다 잠금이 줄어든다. 잠금 파일은 사람이
읽는 JSON 이라 PR 에서 무엇이 잠겼는지 보이고, `hanlint doctor` 가 몇 건이 잠겨 있는지 늘 말한다. 빚을
감추는 자리가 되지 않게 하려는 것이다.

## 잘 읽히는 글을 쓰는 법

규칙은 결국 다섯 가지를 말한다. 각 항목의 오른쪽이 hanlint 가 그것을 세는 방식이다.

### 1. 명사를 쌓지 말고 동사로 되돌린다

한국어는 조사가 관계를 표시한다. 명사만 이어 붙이면 그 표시가 사라지고 독자가 조사를 스스로 끼워 넣는다.

| 고치기 전 | 고친 뒤 |
|---|---|
| 가상환경 생성 후 패키지 설치 확인 절차를 따릅니다 | 가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다 |
| 회사의 팀의 결정의 근거를 봅니다 | 그 팀이 왜 그렇게 정했는지 근거를 봅니다 |

아래쪽처럼 한 문장에 관형격 조사가 셋 이상 나오는 것도 같은 병이라 `nounPile` 과 `euiChain` 이 함께 센다.

### 2. 독자가 누르고 입력할 것을 이름으로 쓴다

가리키는 말은 전부 스크롤을 되돌리게 만든다. 특히 가리킬 대상이 앞 문장에 아예 없으면 독자는 되돌아가도
못 찾는다.

| 고치기 전 | 고친 뒤 |
|---|---|
| 터미널을 엽니다. 이것을 실행합니다 | 터미널을 엽니다. `make_qr.py` 를 실행합니다 |
| 해당 값을 위의 코드에 넣습니다 | `행 수` 칸에 100을 넣습니다 |

그래서 `deixis` 는 가리키는 말을, `danglingDeixis` 는 그중 앞 문장에 대상이 없는 것을 따로 센다.

### 3. 사실을 나란히 놓지 말고 이유로 잇는다

독자는 낱말이 아니라 문장 사이의 이유를 못 따라가서 멈춘다. 짧은 평서문 셋을 붙여 놓으면 그 관계를
독자가 세운다.

> 고치기 전: 병합 셀은 첫 칸에만 값이 있습니다. 나머지 칸은 빈값입니다. 정렬하면 순서가 깨집니다
>
> 고친 뒤: 병합 셀은 첫 칸에만 값이 들어 있고 나머지는 비어 있습니다. 그대로 정렬하면 빈 칸이 값과
> 떨어져 순서가 깨집니다

오른쪽이 더 길지만 읽는 시간은 짧다. `factListParagraph` 가 인과 표지 없는 문단을, `endingRepeat` 이
이유도 질문도 없이 같은 어미만 이어지는 구간을 센다.

### 4. 글 전체의 자기모순

그럼 hanlint 는 맞춤법 검사기와 무엇이 다를까요? 갈리는 자리가 여기다. 문장 하나만 보면 멀쩡한데
**두 자리를 맞대 보면 틀린 것**이 있고, 그것은 글 전체를 들고 있어야 보인다.

- 도입은 `여섯 가지` 라 했는데 결말은 `다섯 가지` 라 센다 (`countMismatch`)
- `뒤에서 다루겠습니다` 라 해 놓고 끝까지 안 나온다 (`promiseRecall`)
- 만들지 않은 파일을 뒤에서 읽는다 (`inputFileSource`)
- 설치 줄에 없는 패키지를 import 한다 (`installImport`)
- 표의 한 열에서 한 칸만 다른 잣대로 쟀다 (`tableOddCell`)
- `453MB 에서 700MB 로 올라갔습니다` 인데 453MB 가 앞에 한 번도 안 나왔다 (`numberOrphan`)

따라 하는 독자는 이런 자리에서 실제로 멈춘다. 문장이 예뻐도 소용이 없다.

### 5. 독자를 부르고 절마다 결과를 남긴다

물음표가 한 번도 없는 글은 독자에게 한 번도 말을 걸지 않은 글이다. 한 절을 다 읽었는데 자기 화면에서
확인할 것이 없으면 그 절은 과정이 아니라 참고 자료다.

| 고치기 전 | 고친 뒤 |
|---|---|
| 파일을 만들 수 있습니다 | 터미널에 `dir` 을 쳐서 파일 이름을 확인해 봅니다 |
| 표가 어디에 생기는지 설명합니다 | 그럼 표는 어디에 생겼을까요? 실행한 폴더에 있습니다 |

`noQuestion` 과 `sectionResult` 가 독자를 부르는 자리를 세는데, 보고서와 참고 문서는 그 계약을 지지
않으므로 `report` 와 `docs` 프리셋이 둘을 끈다.

규칙 하나가 왜 있는지와 그 본보기는 `hanlint explain <규칙>` 이 전부 보여 준다.

### 다시 쓸 틀

위 다섯 가지를 **빈칸이 있는 틀**로도 든다. 본보기가 고친 사례 하나라면 문형은 그 사례를 다시 쓸 수 있는
틀이다. 지적을 받았는데 어떻게 다시 쓸지 모를 때 그 규칙을 피하는 틀만 골라 본다.

```powershell
hanlint patterns --rule nounPile
```

```text
동사로 되돌리기  (nounPile 를 피한다)
  틀    {무엇}을 {한 뒤} {무엇}이 {어떤지} {확인합니다}
  언제  명사가 셋 이상 이어질 때. 조사를 되살려 무엇이 무엇의 목적어인지 보인다
  예시  가상환경을 만든 뒤 패키지가 깔렸는지 확인합니다.
  대신  가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.
  출처  이오덕 우리글 바로쓰기의 명사문을 동사문으로
```

열 개가 있다. 행동과 결과, 확인, 인과 잇기, 이름으로 이어받기, 독자에게 묻기, 값 소개, 동사로 되돌리기,
결핍 도입, 수치 비교, 미룬 것 회수다. 출처는 글쓰기 스킬과 한국 글쓰기 책들 (이오덕 `우리글 바로쓰기`,
이수열 `우리말 우리글 바로 쓰기`, 김정선 `내 문장이 그렇게 이상한가요`, 배상복 `문장기술`) 이다.

**예시는 전부 hanlint 를 error 0 으로 통과한다.** 게이트가 매번 확인하므로 규칙이 바뀌어 틀이 낡으면
빨갛다. 통과가 보장된 틀이라는 것이 이 명령이 파는 것이다.

책들의 조언을 규칙으로 넣으려고 실측했더니 대부분 규칙이 아니었다. 김정선이 든 `것` 은 발행본 다섯
편에서 75건이 걸리는데 표본이 전부 정당했다. 그 조언들은 "이건 틀렸다" 가 아니라 "이 자리를 다시 보라"
는 교정자의 눈이다. 금지로는 못 담고 틀로는 담긴다. 재는 방법과 숫자는
[tests/_attempts/koreanStyleBooks/](tests/_attempts/koreanStyleBooks/) 에 있다.

## AI 초안 검사

AI 가 쓴 한국어는 대체로 문법이 맞고 대체로 밋밋하다. 위 다섯 가지를 정확히 어긴다. 명사를 쌓고, 지시어를
쓰고, 사실을 나란히 놓고, 도입에서 약속한 개수를 결말에서 잊고, 독자를 한 번도 부르지 않는다.

그래서 AI 에게 규칙을 말로 설명하는 대신 **기계가 읽는 지적을 그대로 준다.**

```powershell
hanlint 글.md --format json
```

지적마다 `rule`, `line`, `quote`, `why`와 규칙을 설명하는 `exemplar`가 온다. 교육용 본보기가 실제 수정
성공률을 높이는지는 [exemplarLift 탐침](tests/_attempts/exemplarLift/)에서 따로 쟀다. `qwen3:8b` 실제 문장
30쌍에서 목표 규칙 해결, 새 error 0, 뜻 보존을 함께 만족한 것은 본보기 유무 모두 12/30이었다. 따라서
`writingPacket`은 일반 본보기를 작문 근거로 싣지 않는다.

대신 지적의 정규화한 원문까지 사람이 승인한 `[[patches]]`와 완전히 같을 때만 `patch`와
`guidance.patch`가 붙는다. [patchMemory 탐침](tests/_attempts/patchMemory/)의 고정 9과제에서는 세 조건을
모두 만족한 것이 이유만 제공 2/9, 무조건 본보기 3/9, 정확 재생 4/9이었다. 승인 원문 세 건만 보면 정확
재생이 일반 본보기에 2승 0패 1무였다. 표본이 작으므로 유사 문장으로 넓히지 않는다. 맞는 승인 원문이
없으면 그 패치는 선택하지 않는다.

서로 다른 공개 Git 이력 6곳에서 일대일 문장 고침 3,233쌍을 모아 보호 원자와 연산 서명으로 거른
[operationMemory 탐침](tests/_attempts/operationMemory/)도 따로 했다. 고정 7과제에서 안전한 성공은 이유만
2/7, 무조건 본보기 1/7, 정확 재생 2/7, 표면 연산 4/7이었다. 표면 연산은 정확 재생에 2승 0패 5무였고,
위험한 의미 전이 세 건은 모두 선택하지 않았다. 그래서 이긴 표면 치환만 `guidance.operation`으로 내고,
지시어와 의미 고침은 계속 원문 완전 일치에 남긴다. 맞는 패치나 연산이 없으면 `guidance`는 비고 모델은
확실하지 않은 문장을 그대로 둔다.

에이전트에 붙일 때는 [skills/use-hanlint/SKILL.md](skills/use-hanlint/SKILL.md) 를 스킬 폴더에 둔다.
글을 쓴 직후 스스로 검사하고 error 가 0 이 될 때까지 고친 뒤에 사람에게 넘긴다.

## 평가 루프에서의 자리

hanlint 는 **0층**이다. 좋은 글인지는 판정하지 않는다.

```text
쓴다
 ↓
0층  hanlint            결정적. 고치면 확실히 0 이 된다. 0 이 될 때까지 여기서만 돈다
 ↓
1층  규칙 위반 (LLM)     기계가 못 재는 규칙만 남는다
2층  규칙 밖 읽힘 (LLM)  지루한가, 몰입이 끊기는가, 검색 의도에 답하는가
 ↓
지적 없음 → 끝
```

블로그 글 한 편을 LLM 평가자 넷이 네 라운드 읽었더니 지적이 31, 27, 40, 16 건으로 줄지 않았다. 마지막
16건의 절반이 세면 잡히는 것이었다. 평가자는 라운드마다 다른 것을 발견하므로 셀 수 있는 것에 화력을 쓰면
루프가 수렴하지 않는다. 0층이 바닥을 깔아야 위층이 자기 일을 한다.

## 명령 한눈에

| 명령 | 무엇 | npm |
|---|---|---|
| `hanlint` | 첫 화면. 이 폴더의 파일 이름으로 만든 예시와 다음 걸음 | 예 |
| `hanlint 글.md` 또는 `hanlint 글들/` | 검사한다. 폴더면 그 아래 마크다운 전부 | 예 |
| `hanlint watch 글.md` | 저장할 때마다 다시 검사한다 | 아니오 |
| `hanlint fix 글.md` | 번역투, 명령형 뒤 마침표, 이중 부정처럼 확실한 자리를 고친다 | 예 |
| `hanlint explain <규칙>` | 규칙의 기술서와 본보기. 오타면 가까운 이름을 준다 | 예 |
| `hanlint patterns --rule <규칙>` | 그 규칙을 피하는 문장 틀. 예시는 error 0 이 보장된다 | 예 |
| `hanlint rules` | 규칙 목록. 부류로 묶고 꺼진 것을 표시한다 | 예 |
| `hanlint baseline 글들/` | 지금 있는 지적을 잠근다. `--prune` 은 죽은 잠금을 치운다 | 예 |
| `hanlint 글들/ --baseline` | 잠근 것은 넘기고 새로 생긴 것만 막는다 | 예 |
| `hanlint 글.md --preset docs` | 설정 파일 없이 이번 검사의 글 종류만 정한다. 종류는 blog, report, docs, guide, essay, fiction, encyclopedia 이고 규칙 묶음과 견줄 프로파일이 따라온다 | 예 |
| `hanlint doctor` | 어느 설정을 읽었고 어느 분석기로 돌며 어느 규칙이 꺼져 있는지 | 예 |
| `hanlint init --preset docs` | 글의 종류에 맞춘 `hanlint.toml` | 예 |
| `hanlint 글.md --format compact --errors-only` | 한 줄에 지적 하나, error 만. 스크립트가 쓴다 | 예 |
| `hanlint 글.md --format json` | 본보기가 붙은 기계 판. `github` 은 GitHub Actions 주석 | 예 |
| `hanlint rules --format json` | 규칙 전부를 기술서와 본보기와 함께. 에이전트가 훑을 때 | 예 |
| `hanlint explain <규칙> --format json` | 규칙 하나의 기술서와 본보기와 틀을 한 덩어리로 | 예 |
| `hanlint - --path 초안.md` | stdin 으로 넣은 글을 그 이름으로 검사한다 | 예 |
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
| `hanlint arena judge-cases / judge-consistency / judge-evaluate` | 자동 심사기의 좌우 위치 편향을 먼저 재고 사람 합의가 있을 때만 정확도와 calibration을 낸다 | 아니오 |
| `hanlint profile build 글들/` | 참조 글의 분포 (프로파일). `--profile` 로 종류의 프로파일 대신 그것과 견준다 | 아니오 |
| `hanlint terms 글.md` | 한국어 학습용 어휘 C에만 등재된 화제어의 첫 자리를 찾는다. `--outside` 는 목록 밖 후보도 보인다 | 아니오 |
| `hanlint coverage review.json 글.md` | 사람 평가자의 지적 가운데 hanlint 가 같은 자리를 집은 비율 | 아니오 |

종료 코드는 지적이 없으면 0, error 가 있으면 1 이라 발행 게이트에 그대로 물린다. npm 칸이 아니오 인 명령은
파이썬 패키지 (`pip install hanlint`) 에만 있고 `npx hanlint` 로 부르면 무엇을 대신 쓰라는 안내와 함께 2 로
끝난다. 두 판 모두에 있는 명령은 같은 규칙, 같은 fixture, 같은 출력이다.

## 규칙을 끄기

프리셋 위에서 더 끄려면 `hanlint.toml` 의 `disable` 에 이름을 넣는다. 한 자리에서만 끄려면 마크다운
주석을 쓴다. 상투어를 인용하는 문단처럼 규칙이 맞지만 그 자리만 예외일 때다.

```markdown
<!-- hanlint-disable cliche -->

AI 가 자주 쓰는 표현은 `핵심은`, `결국 중요한 것은` 처럼 눈에 띄는 것부터 지웁니다.

<!-- hanlint-enable cliche -->
```

`hanlint-disable-next` 는 다음 블록 하나만 끈다. 규칙 이름을 안 적으면 전부 끈다. 백틱과 따옴표 안은
인용이라 사전 규칙과 지시어 규칙이 처음부터 건너뛴다.

규칙이 아니라 글의 형식이 다르면 끄지 말고 설정으로 말한다. 강의 교안처럼 절 제목 아래에 문장형 부제를 두면
`headingSentenceMaxLevel = 2`, 장면 계약이나 도표 원문처럼 코드도 산문도 아닌 펜스가 있으면
`ignoreFences = ["course-scene", "mermaid"]` 다. 실측: 강의 여섯 편에 그냥 돌리면 error 89건이었고 이 둘을
적자 27건이 남았다. 남은 것은 전부 문장의 결함이었다.

## 파이썬에서

```python
from hanlint import lintText

for finding in lintText(text):
    print(finding.line, finding.rule, finding.why)
```

`lintFile`, `auditText`, `fingerprint` 도 같은 자리에 있다.

## CI 게이트로 물린다: pre-commit, GitHub Actions

pre-commit 훅과 GitHub Action 이 저장소 루트에 있다. 훅은 `.pre-commit-config.yaml` 에서 이 저장소를
가리키면 되고, 액션은 지적을 PR 의 줄 주석으로 단다. 쓰는 동안 계속 보려면 `hanlint watch 글.md` 가
저장할 때마다 다시 검사한다.

```yaml
- uses: eddmpython/hanlint@main
  with:
    files: docs/글.md
    errors-only: "true"
```

이미 문서가 쌓인 저장소면 `hanlint baseline docs/` 로 한 번 잠그고 `.hanlint-baseline.json` 을 커밋한다.
그러면 첫날부터 초록이고, 그 뒤로 누가 문장을 고치거나 새로 쓸 때만 막힌다.

## 무엇을 잡고 무엇은 안 잡나

경계는 [skills/specs/start/product.md](skills/specs/start/product.md) 에 있다. 안 잡는 것도 근거와 함께
적혀 있다. 뜻을 이해해야 잡히는 것, 취향, 그리고 만들었다가 실측에서 오탐이 이겨 뺀 규칙들이다.

규칙 하나는 파일 하나이고 자기 기술서를 docstring 으로 든다. 규칙마다 어떤 실제 글의 어떤 문장에서
왔는지가 거기 적혀 있다. 실측 없는 규칙은 넣지 않는다.

## 오탐 신고와 규칙 제안

정당한 문장이 잡혔거나 잡아야 할 자리를 놓쳤으면 이슈로 알려 주면 된다. 양식 두 개가 문장 원문과 근거를
묻는다. 오탐은 fixture 의 spare 로 박혀 다시는 잡히지 않게 되고, 제안은 실측 사례가 있어야 규칙이 된다.
절차는 [skills/specs/operation/feedback.md](skills/specs/operation/feedback.md) 에 있다.

## English

hanlint is a linter for Korean prose in Markdown. It reports only what can be decided by counting:
translationese, noun pile-ups, double passives, dangling demonstratives, fragmented paragraphs and
document-level structure. It does not judge whether writing is good, and it is not a spell checker.

Two implementations, zero runtime dependencies, identical output: `pip install hanlint` and
`npx hanlint`. Exit code is 1 when an error-level finding exists, so it drops into CI as a gate.
`hanlint baseline docs/` locks what already exists so an established repository starts green.

## 라이선스

코드는 MIT 다. 배포물이 함께 싣는 외부 자료 둘은 라이선스가 다르다.

| 무엇 | 라이선스 | 고지 |
|---|---|---|
| hanlint 코드와 나머지 데이터 | MIT | `LICENSE` |
| `evidenceEntailmentV1.json` (KLUE-NLI 파생 36개 사례) | CC BY-SA 4.0 | `src/hanlint/data/evidenceEntailmentV1.LICENSE.md` |
| `learningVocabulary.tsv`, `easyWords.toml` (국립국어원) | 공공누리 제1유형 | `src/hanlint/data/koglType1.LICENSE.md` |

배포 메타데이터의 표현식은 `MIT AND CC-BY-SA-4.0 AND LicenseRef-KOGL-Type-1` 이고 세 고지 파일이
휠과 sdist 에 함께 들어간다. 기준 말뭉치의 원문은 저장소 밖에 있고 배포물에 싣지 않는다.
