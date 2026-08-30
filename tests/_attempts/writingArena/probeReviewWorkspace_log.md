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

## 아직 확인하지 못한 것

실행 환경에 연결된 브라우저가 0개라 실제 화면의 클릭, 새로 열어 진행 재개, 키보드 이동과 다운로드는
실행하지 못했다. 다른 브라우저 자동화로 바꾸지 않았고 이 항목을 통과로 기록하지 않는다. 연결된
브라우저에서 일곱 사례를 열어 이 네 동작을 확인한 뒤 탐침을 닫는다.

이 탐침은 평가 작업대의 계약과 실행 가능성만 확인한다. 실제 평가자가 남긴 선호가 없으므로 자연스러움,
명료성, 독자 과업이나 목소리 향상을 주장할 근거가 아니다.
