---
id: operation.usage
title: 용례 엔진
category: operation
purpose: 라이선스가 확인된 실제 글에서 낱말이 어떻게 쓰였는지를 규칙과 명령에 대는 경계. 무엇을 싣고 무엇을 사용자 기계에만 두는지, 표를 다시 만드는 절차.
whenToUse:
  - nounPile 이 어떤 연쇄를 왜 접는지 알고 싶다
  - 빈도표를 다시 만들거나 글 종류를 더한다
  - 말뭉치의 라이선스를 판정한다
verify:
  - .venv/Scripts/python.exe -X utf8 -B -m pytest tests/usage tests/gates/testUsageCounts.py -q
status: observed
---

# 용례 엔진

hanlint 는 좋은 글을 판정하지 않는다. 용례 (usage) 는 그 원칙 안에서 하나를 더한다. **이 낱말 조합이 그 종류의
실제 글에서 쓰이는가** 를 결정적으로 답한다. 판정은 여전히 사람과 LLM 의 몫이고, hanlint 는 근거를 댄다.

## 무엇이 어디에 사나

| 일 | 자리 | 층 |
|---|---|---|
| 명사 연쇄 뽑기 `nounRuns` | `src/hanlint/analysis/tokenize.py`, `npm/src/analysis/tokenize.js` | analysis |
| 빈도표 읽기와 조회 (`usageKindOf`, `attested`, `chainDocuments`) | `src/hanlint/usage/counts.py`, `npm/src/usage/counts.js` | usage |
| 빈도표 자료 | `src/hanlint/data/usageCounts.<종류>.json` (npm 은 투영) | data |
| 빈도표 만들기 | `scripts/derive/usageCounts.py` | 도구 |
| 말뭉치 받기 | `scripts/fetch/dartReports.py` (report) | 도구 |
| 실측 | `scripts/measure/reports.py` | 도구 |
| 규칙 | `nounPile` 이 관용 연쇄를 접는다 | rules |

프리셋 → 종류는 `config.USAGE_OF` 가 정한다 (report 만). 설정 `usageKind` 가 덮고 빈 문자열이면 보지 않는다.
`usageMin` (기본 3) 은 연쇄가 몇 편의 문서에 나와야 관용으로 보는지다.

## 빈도표의 계약

- 키는 `nounRuns` 가 뽑은 어절들을 빈칸 하나로 이은 것. 규칙이 같은 함수로 뽑아 그대로 찾으므로 연쇄의 뜻은 한 곳
  (`analysis/tokenize.py`) 에만 있다.
- 값은 그 연쇄가 나온 **문서 수** 다. 한 문서 안의 반복은 한 번이다. 한 회사의 버릇은 관용이 아니다.
- 센 길이 4 미만과 한 문서에만 나온 연쇄는 넣지 않는다. 글자 하나짜리 어절만 이어진 연쇄 (띄어 쓴 제목의 잔해) 도 뺀다.
- 파일 하나가 256 KiB 를 넘지 않는다. 패키지와 브라우저 묶음에 그대로 실린다.
- `tests/gates/testUsageCounts.py` 가 위를 지킨다. 상수의 정본은 `scripts/derive/usageCounts.py` 다.

## 규칙이 접는 방식

nounPile 은 문장의 긴 연쇄 (nounPileMin 이상) 가 **전부** 표에 usageMin 편 이상으로 있을 때만 그 문장을 넘긴다.
관용 연쇄에 명사를 하나 더 얹은 것 (`정관상 배당절차 개선방안 이행 가부 검토 결과`) 은 여전히 쌓기다. 부분 일치와
창 (window) 으로 접지 않는다. 관용 낱말 둘을 붙인 것도 관계가 표시되지 않은 쌓기이기 때문이다.

## 다시 만들기

```
DART_API_KEY=... python -X utf8 -B scripts/fetch/dartReports.py --count 1000
python -X utf8 -B scripts/derive/usageCounts.py --kind report
python -X utf8 -B scripts/derive/npmData.py
python -X utf8 -B scripts/measure/reports.py
```

말뭉치는 `~/.cache/hanlint/corpus/dart/` 에 있고 저장소에 들어오지 않는다. 키는 환경 변수로만 준다.
빈도표를 다시 만들면 `nounPile` docstring 의 실측 수치와 `config.usageMin` 의 근거를 같은 커밋에서 맞춘다.

## 라이선스 판정 (2026-09-19)

- OpenDART 이용약관 (제16조 ①, 제23조 ①, 제16조 ④): 프로그램의 저작권은 금융감독원, 공시정보는 제출인 책임, 나머지는
  저작권법과 공공데이터법. 재배포를 허용하는 조항도 금지하는 조항도 없다. **문장은 사용자 기계에만 두고 통계인
  빈도표만 싣는다.** 출처는 접수번호와 DART 주소다.
- 정책브리핑 (korea.kr) 의 공공누리 제1유형 텍스트는 출처 표시로 자유 이용이다. 문장까지 실을 수 있는 다음 report
  말뭉치 후보다.

## 실측 (사업보고서 961편, 2026-09-19)

수치는 `scripts/measure/reports.py` 가 다시 낸다. `nounPile` docstring 과 `config.usageMin` 이 근거로 인용한다.

- 문단 514,211개, 문장 747,583개. 문장 길이 평균 14.7 어절 (중앙 12, p90 28), longSentenceMax 30 초과 8.2%.
  명사 연속 5 이상인 문장 0.6%. `의` 3회 이상인 문장 9.0%.
- 1,000문장당 지적: translationese 293.9, euiChain 98.5, longSentence 82.3, nounPile 6.2 → 4.8 (용례 접기 뒤).
- nounPile 이 짚은 연쇄 5,011건 3,355종. 다른 문서 N편 이상에 나온 비율 (leave-one-out): N=2 22.4%, N=3 21.0%,
  N=5 19.8%, N=10 18.7%, N=20 16.6%. 셋부터의 차이가 작아 usageMin 기본은 3 이다.
- 같은 문장이 둘 이상의 문서에 나온 비율 47.4% (회계정책 주석과 양식 문구). 문장 색인은 같은 문장을 하나로 접고
  문서 수를 함께 보여야 한다.
- 빈도표 (길이 4 이상, 2편 이상): 778종, 36,839 바이트.
- 발견한 것 (이 일의 범위 밖): translationese 가 보고서 문장의 29% 를 짚는다 (`에 대한`, `을 통해` 가 보고서의 관용인지
  사전이 넓은지 실측이 필요하다). `개선하고자` 처럼 `-고자` 로 끝난 어절을 명사로 본다 (꼬리 사전에 없다).
  DART 원문 자체가 항목 이름과 본문을 띄우지 않은 자리 (`제안 주체해당 사업목적`) 가 있어 그 연쇄가 표에 든다.
