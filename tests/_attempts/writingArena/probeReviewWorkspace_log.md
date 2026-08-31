# writingArena 오프라인 평가 작업대 탐침

## 질문

고정 일곱 장르 suite를 평가자 한 명에게 정체성과 원래 식별자를 숨겨 배정할 수 있는가. 단일 HTML이
사람의 판정을 미리 만들지 않으면서 content 우선 규칙, voice 기권, 진행 저장과 JSON 회수를 맡을 수 있는가.

## 고정 실행

2026-08-31에 `writingArenaPilotV1.json`과 seed `20260831`을 사용했다. 평가자 가명은
`pilot-human-a`, group은 `targetReader`로 고정했다.

```console
hanlint arena panel writingArenaPilotV1.json --seed 20260831 --output suite.json
hanlint arena assign suite.json --evaluator-id pilot-human-a --group targetReader --output assignment-a.json
hanlint arena review-page suite.json assignment-a.json --output review-a.html
```

산출물은 다음과 같았다.

| 파일 | 바이트 | SHA256 |
|---|---:|---|
| `suite.json` | 18,905 | `3cdd748d1c237ceba487b154d1717ea57edbb7d5ff1fa2ef6ed70a85be8e2d06` |
| `assignment-a.json` | 16,773 | `8a8b8d737051ec315dc2413c698bb25faa3d6946d39541c4c7423eb16e8a9ba9` |
| `review-a.html` | 43,587 | `b76c18b80e37b9f126e5764bc3ce3ba5845eac511d6ba330b53e7b73182813c3` |

## 확인한 결과

- assignment에는 `case-001`부터 `case-007`까지만 있었다. 원래 suite와 case 식별자는 없었다.
- 일곱 사례의 좌우 전환은 평가자 가명에서 결정됐고 한 assignment 안에서 3 대 4로 균형을 이뤘다.
- content와 네 선호의 템플릿 값은 모두 빈 문자열이었다. 시스템이 사람의 품질 label을 만들지 않았다.
- 변조한 글, 사례 해시, 평가자와 case 누락은 import 전에 거부됐다. 회수한 좌우 선택은 원래 suite 방향으로 복원됐다.
- HTML에는 외부 자원, 네트워크 API와 HTML 삽입 sink가 없었다. CSP는 연결을 막고 assignment 해시별
  브라우저 저장만 사용한다.
- 목표·CLI·누출 게이트 84개, 전체 Python 713개와 npm 109개가 통과했다.
- Python 3.14에 wheel을 새로 설치했다. 설치본에 HTML과 schema가 있었고 설치본 CLI도 같은 세 산출물을 만들었다.

## 실제 브라우저 확인

2026-09-01에 프로젝트 잠금 파일의 정확 버전 pyproc과 격리된 Microsoft Edge 프로필로 남은 항목을
확인했다. 공통 실행 공간에서 같은 seed로 suite를 다시 만들고 평가자 `visual-qa-20260901`에게 배정했다.

| 파일 | 바이트 | SHA256 |
|---|---:|---|
| `suite.json` | 18,905 | `f62f9cc5b5cd1125cd58cbdc9e8aff9dac21e5cf6855b78d73b2f197aa71286b` |
| `assignment.json` | 16,783 | `fc77c7400f779082bd38bb31e6bd1c2cc1e23d03bcd26389c69cb9ba5069f2d6` |
| `review.html` | 46,148 | `e5af381846c069c50a38e072c563b5897c77f77cca11df12141daa4102fba7c3` |
| 내려받은 review JSON | 5,707 | `b2107dab85dcfa6e3fa759fff9640a361fbe885895d967439165f2d562ca6e07` |

- 데스크톱 1440 x 1000에서 일곱 장르 화면과 1425 x 2894 전체 페이지를 눈으로 봤다. 두 글 비교,
  context 카드, 진행 막대, 판정 폼과 내보내기 영역에 겹침과 가로 잘림이 없었다.
- 모바일 390 x 844에서 일곱 장르 화면과 390 x 4447 전체 페이지를 눈으로 봤다. 두 열은 한 열로 접혔고
  라디오, 근거 입력과 작업 버튼이 화면 폭 안에서 읽혔다.
- 첫 실제 라디오 클릭은 화면만 선택된 채 저장되지 않았다. content 변경 처리기의 정의되지 않은
  `bothContentPass` 호출이 원인이었다. `hanlintReview.bothContentPass`로 고친 뒤 같은 시나리오를 처음부터
  다시 실행했다.
- content 두 항목을 pass로 고른 뒤 세 선호를 실제로 클릭했다. 목소리 표본이 없는 일곱 사례의 voice는
  모두 판단 불가로 잠겼다. 다섯 근거를 채우면 완료 수와 탐색 버튼의 완료 표시가 함께 바뀌었다.
- 첫 사례를 완성하고 Alt+오른쪽을 누르자 보고문 사례로 이동했고 제목이 실제 접근성 초점을 받았다. target을
  닫고 같은 격리 프로필에서 다시 열어도 둘째 사례와 첫 완료 기록이 복원됐다.
- 일곱 사례를 끝낸 뒤 받은 `hanlint.panelAssignmentReview` JSON은 assignment SHA256과 review 7건이
  일치했다. 다운로드 바이트를 SHA256으로 다시 확인한 뒤 아티팩트를 지웠다.
- 데스크톱과 모바일 모두 detach와 target 종료 뒤 session, locator, artifact, transport와 perception 자원
  수가 시작값 0으로 돌아왔다.

이 탐침은 평가 작업대의 계약과 실행 가능성만 확인한다. 실제 평가자가 남긴 선호가 없으므로 자연스러움,
명료성, 독자 과업이나 목소리 향상을 주장할 근거가 아니다.
