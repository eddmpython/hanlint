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
| 빈도표 읽기와 조회 (`usageKindOf`, `attested`, `conventional`) | `src/hanlint/usage/counts.py`, `npm/src/usage/counts.js` | usage |
| 빈도표 자료 | `src/hanlint/data/usageCounts.<종류>.json` (npm 은 투영) | data |
| 빈도표 만들기 | `scripts/derive/usageCounts.py` | 도구 |
| 말뭉치 받기 | `scripts/fetch/dartReports.py` (report) | 도구 |
| 실측 | `scripts/measure/reports.py` | 도구 |
| 문장 역인덱스 만들기와 조회 (`buildIndex`, `loadIndex`, `UsageIndex.search`, `UsageIndex.collocations`) | `src/hanlint/usage/sentences.py`, `npm/src/usage/sentences.js` | usage |
| 위키백과 받기 | `scripts/fetch/koWikipedia.py` (`--namespaces` 가 장르를 고른다. 0 본문, 4 지침, 12 도움말) | 도구 |
| 규칙 | `nounPile` 이 관용 연쇄를 접고, 사전 규칙 다섯 (translationese, hardWord, cliche, redundantPair, japaneseLoan) 이 관용 항목을 접는다 (`rules/shared/dictionaryRule.py`) | rules |
| 명령 | `hanlint usage "낱말 …" --kind report --limit 5`, `hanlint usage build <종류> <글 폴더>`, `hanlint usage kinds` (두 판) | cli |
| 스킬 | `write-korean` 의 `더 있는 것` 과 `use-hanlint` 4단계 (막힌 자리) 가 `usage` 를 가리킨다 | |

프리셋 → 종류는 `config.USAGE_OF` 가 정한다 (report 만). 설정 `usageKind` 가 덮고 빈 문자열이면 보지 않는다.
`usageMin` (기본 3) 은 연쇄가 몇 편의 문서에 나와야 관용으로 보는지, `usageShare` (기본 0.9) 는 사전 항목이 문서 몇 할에
나와야 관용으로 보는지다. 연쇄는 존재를 묻고 (셋만 있어도 낱말이다) 항목은 비율을 묻는다 (번역투는 어디에나 조금은 있다).

## 빈도표의 계약

표 하나에 두 절이 있다. `chains` (명사 연쇄 → 문서 수) 와 `patterns` (사전 → 항목 pattern 원문 → 문서 수).

- 키는 `nounRuns` 가 뽑은 어절들을 빈칸 하나로 이은 것. 규칙이 같은 함수로 뽑아 그대로 찾으므로 연쇄의 뜻은 한 곳
  (`analysis/tokenize.py`) 에만 있다.
- 값은 그 연쇄가 나온 **문서 수** 다. 한 문서 안의 반복은 한 번이다. 한 회사의 버릇은 관용이 아니다.
- 센 길이 4 미만과 문서 셋 미만에 나온 연쇄는 넣지 않는다 (usageMin 의 기본과 같다). 글자 하나짜리 어절만 이어진 연쇄
  (띄어 쓴 제목의 잔해) 도 뺀다.
- `patterns` 는 산문 사전 다섯 (translationese, cliches, redundantPair, japaneseLoan, easyWords) 의 내장 항목만 든다. 키는
  사전 파일에 적힌 pattern 원문이라 두 판이 같은 키를 갖는다. 설정으로 더한 항목은 표에 없어 늘 짚는다.
- 파일 하나가 256 KiB 를 넘지 않는다. 패키지와 브라우저 묶음에 그대로 실린다.
- `tests/gates/testUsageCounts.py` 가 위를 지킨다. 상수의 정본은 `scripts/derive/usageCounts.py` 다.

## 규칙이 접는 방식

nounPile 은 문장의 긴 연쇄 (nounPileMin 이상) 가 **전부** 표에 usageMin 편 이상으로 있을 때만 그 문장을 넘긴다.
관용 연쇄에 명사를 하나 더 얹은 것 (`정관상 배당절차 개선방안 이행 가부 검토 결과`) 은 여전히 쌓기다. 부분 일치와
창 (window) 으로 접지 않는다. 관용 낱말 둘을 붙인 것도 관계가 표시되지 않은 쌓기이기 때문이다.

사전 규칙은 맞은 항목이 그 종류의 문서 usageShare 이상에 나오면 그 매치를 넘긴다. 사업보고서 3,193편에서 translationese
항목 여덟 (`에 대한`, `에 관한`, `에 대해`, `로부터`, `을 위해`, `에 의해`, `로 인해`, `을 통해`) 이 99% 이상, `상기` 97%,
`를 가지고 있` 93% 에 나왔고 다음은 `에 있어서` 74% 다. 열 편 가운데 아홉 편이 쓰는 표현은 그 종류의 말이고, 그것을 report
에서 짚는 것은 결함이 아니라 문체를 짚는 것이다. blog 와 docs 에는 표가 없어 그대로 짚는다.

## 문장 역인덱스

`hanlint usage build <종류> <글 폴더>` 가 `~/.cache/hanlint/usage/<종류>/` 에 만든다. 파일 꼴과 토큰과 순서는
`src/hanlint/usage/sentences.py` 의 docstring 이 소유하고 npm 판은 같은 바이트를 만든다 (`testUsageIndexAgrees`).
색인이 유일한 구조다. 임베딩과 예측 모델은 두지 않는다. 이 판단은 agipath (같은 운영자의 연구) 가 위키 1,341만 문장과
우리말샘 134만 문장에서 임베딩과 예측을 다 시도한 뒤 "역인덱스가 유일한 기본 구조" 로 돌아온 기록 위에 있다. 여기서는
만드는 건 LLM 이고 색인은 사실을 댄다.

- 입력: 폴더의 txt 와 md (파일 하나가 문서 하나) 와 jsonl (줄 하나가 문서 하나). 문서 순서는 폴더 기준 posix 경로의
  코드 포인트 순이라 OS 와 판이 달라도 같다.
- 만들기: 문장 표와 위치 표는 바로 파일에 쓰고 postings 는 25만 문장마다 조각으로 내린 뒤 토큰 순으로 병합한다. 결과는
  한 번에 만든 것과 바이트 단위로 같다 (시험이 조각 4 로 줄여 견준다). 같은 문장은 SHA-256 앞 8바이트로 접어 문장
  1,300만 개의 키를 글자로 들지 않는다.
- 함께 쓰는 말: 표를 따로 만들지 않는다. 조회 때 그 낱말의 postings 앞 5,000문장을 읽어 바로 앞뒤 어절을 문서 수로
  센다. 뒤 용언은 꼬리 사전으로 어간을 떼고 (`감소하였습니다` → 감소), 한 글자 꼬리 (서, 고, 며) 는 하/되 뒤에서만
  용언으로 보며, 연결 어절 (`data/collocationStops.txt`: 및, 따라, 인해 …) 과 의존명사 (`nonNouns.txt`) 는 세지 않는다.
  실측: `리스부채` 뒤 용언 인식 411편, 포함 175편, 측정 131편 (사업보고서 3,193편, 2026-09-19).

- 문장: 마침표나 물음표나 느낌표로 끝난 한국어 문장만. 제목과 항목 이름은 낱말의 쓰임이 아니라 이름이라 빈도표 쪽이다.
  코드 펜스 안과 표 줄은 넘기고 목록 표시와 항목 번호는 뗀다.
- 접기: 공백을 모으고 숫자를 0 으로 바꾼 꼴이 같으면 한 문장이다. 몇 편의 문서에 나왔는지를 세어 결과에 보인다.
  실측: 사업보고서 961편에서 마침표로 끝난 문장을 접으니 343,149문장이 남았다.
- 토큰: 조사를 뗀 어절 (core) 과 세 글자 이상 한글 어절의 글자 두 개짜리 조각 (bigram). bigram 이 `금융리스부채` 와
  `리스부채`, `적용되며` 와 `적용된다` 를 잇는다. 문장 절반 넘게 나오는 토큰은 조회에서 뺀다.
- 순서: BM25 (k1 1.5, b 0.75) 값 내림차순, 같으면 문장 번호 오름차순. 이 값은 낱말 겹침이지 글의 판정이 아니다. 두 판의
  log 가 마지막 자리에서 갈릴 수 있어 1e6 배의 정수로 내려 견준다.
- 크기와 시간 (2026-09-19). report (사업보고서 3,193편, 문장 1,056,316개): 색인 414 MB, 만들기 node 4분 30초,
  조회 1초 안팎. encyclopedia (위키백과 592,264편, 문장 8,844,533개, 토큰 679만 종): 색인 2.4 GB, 만들기 node
  29분 40초, 조회 node 2.6초 파이썬 4.4초 (대부분 함께 쓰는 말의 표본 4,000문장을 디스크에서 찾아 읽는 시간).
  메모리는 길이 표와 문서 수 표와 접은 문장의 해시만 드므로 문장 884만 개에서도 1 GB 안쪽이다.

## AI 가 바로 쓰기

에이전트가 한국어를 쓰기 전에 부르는 자리다. 세 줄이면 된다.

```console
hanlint usage kinds                                   # 이 기계에 어떤 종류의 색인이 있나
hanlint usage "리스부채" --kind report --format json   # 함께 쓰는 말과 문장
hanlint usage build report 글들/                      # 없으면 만든다 (사용자가 정한다)
```

`--format json` 의 꼴 (`version` 2):

```json
{
  "kind": "report", "query": "리스부채", "documents": 3193, "sentences": 1056316,
  "words": [{"term": "리스부채", "sampled": 4000,
             "predicates": [["인식", 411], ["포함", 175]],
             "following": [["제거", 164]], "preceding": [["경우", 17]]}],
  "hits": [{"text": "…", "documents": 1, "source": "20260331004385", "score": 29557084}]
}
```

- `words[].predicates` 는 그 낱말 바로 뒤에 오는 용언의 어간과 **문서 수** 다. `following` 과 `preceding` 은 뒤와 앞의
  명사다. `sampled` 는 그 수를 센 문장 수다 (표본이지 전수가 아니다).
- `hits[].source` 는 출처다. report 는 DART 접수번호 (`https://dart.fss.or.kr/dsaf001/main.do?rcptNo=<번호>`),
  encyclopedia 는 위키백과 글 제목이다.
- `score` 는 낱말 겹침의 크기이지 글의 판정이 아니다. 문장의 사실과 숫자를 결과로 옮기지 않는다.
- 색인이 없으면 종료 코드 2 와 함께 있는 종류와 만드는 법을 낸다. 에이전트는 거기서 멈추고 사용자에게 묻는다.
- 스킬은 `write-korean` 의 `더 있는 것` 과 `use-hanlint` 4단계 (고치다 막힌 자리) 가 이 명령을 가리킨다. 둘 다 묻는
  자리에서 부르는 것이지 절차의 필수 단계가 아니다. 프롬프트에 붙이면 고침이 나아진다는 실측은 없다
  (`tests/_attempts/usageLift`: 300쌍, 두 모델, 사전 등록 조건 셋을 하나도 못 넘었다. 강한 모델 p 1.0000).

## 다시 만들기

```
python -X utf8 -B scripts/fetch/koWikipedia.py            # 위키백과 본문 → ~/.cache/hanlint/corpus/wiki/kowiki.jsonl
python -X utf8 -B scripts/fetch/koWikipedia.py --namespaces 4,12   # 지침과 도움말 → kowiki.ns4-12.jsonl (덤프 재사용)
npx hanlint usage build encyclopedia ~/.cache/hanlint/corpus/wiki
DART_API_KEY=... python -X utf8 -B scripts/fetch/dartReports.py --count 4000
python -X utf8 -B scripts/derive/usageCounts.py --kind report
python -X utf8 -B scripts/derive/npmData.py
python -X utf8 -B scripts/measure/reports.py
python -X utf8 -B -m hanlint usage build report ~/.cache/hanlint/corpus/dart
```

말뭉치는 `~/.cache/hanlint/corpus/dart/` 에 있고 저장소에 들어오지 않는다. 키는 환경 변수로만 준다.
빈도표를 다시 만들면 `nounPile` docstring 의 실측 수치와 `config.usageMin` 의 근거를 같은 커밋에서 맞춘다.

## 라이선스 판정 (2026-09-19)

- OpenDART 이용약관 (제16조 ①, 제23조 ①, 제16조 ④): 프로그램의 저작권은 금융감독원, 공시정보는 제출인 책임, 나머지는
  저작권법과 공공데이터법. 재배포를 허용하는 조항도 금지하는 조항도 없다. **문장은 사용자 기계에만 두고 통계인
  빈도표만 싣는다.** 출처는 접수번호와 DART 주소다.
- 정책브리핑 (korea.kr) 의 공공누리 제1유형 텍스트는 출처 표시로 자유 이용이다. 문장까지 실을 수 있는 다음 report
  말뭉치 후보다.
- 위키백과 (encyclopedia) 는 CC BY-SA 4.0 이다. 출처 (글 제목) 를 붙이면 문장도 나눌 수 있고 같은 조건으로 나눠야
  한다. 그래도 색인은 사용자 기계에만 둔다 (2.4 GB 는 패키지에 실을 크기가 아니다).

## 실측 (사업보고서 961편, 2026-09-19)

수치는 `scripts/measure/reports.py` 가 다시 낸다. `nounPile` docstring 과 `config.usageMin` 이 근거로 인용한다.

### 3,193편 표와 1,000편 실측 (같은 날, 뒤에 한 것)

표는 3,193편 전부에서 만들었다 (연쇄 1,602종, 사전 항목 87개, 78 KB). 지적률은 앞 1,000편 (814,000문장) 을 용례 없이
(`usageKind = ""`) 와 있이 두 번 돌려 같은 문서에서 견줬다 (1,000문장당).

| 규칙 | 용례 없이 | 용례 있이 |
|---|---:|---:|
| translationese | 290.9 | 9.0 |
| hardWord | 22.1 | 9.9 |
| nounPile | 6.6 | 4.9 |
| 그 밖 (euiChain, longSentence, paraFragment …) | 347.9 | 347.9 |
| 합계 | 667.6 | 371.8 |

report 프리셋의 지적이 44% 준다. 준 것은 전부 문서의 90% 이상이 쓰는 표현이고 남은 translationese 9.0 은 `에 있어서`,
`가능하다`, `으로의`, `에도 불구하고` 처럼 보고서 안에서도 고칠 수 있는 자리다. 문장 역인덱스는 3,193편 1,056,316문장,
414 MB, 만들기 3분 24초, 조회 파이썬 1.3초 (그중 실행기 시작 0.4초) 와 node 0.5초다.

### 961편 (처음 잰 것)

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
