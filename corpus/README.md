# 기준 말뭉치

형태 층, 문체 맞춤, 후보 엔진의 범위는 실제 글에서 잰다. 자료원과 선택 조건은
`catalogue.toml`, 선택된 문서와 판본과 원문 해시는 `documents.json` 이 소유한다. 원문은 저장소 밖
`../hanlint.out/corpus/` 에 받는다.

## 자료원과 범위

일곱 종류를 한 자료원에 기대지 않는다. Kubernetes 한국어 사이트에서 블로그, 기술 문서, 단계별 안내를
받고, MDN 한국어에서 기술 문서를, 한국어 위키뉴스에서 보고문을, 한국어 위키문헌에서 1930년대 수필과 소설을,
한국어 위키백과의 알찬 글과 좋은 글 (심사를 거친 글) 에서 백과 설명문을 받는다. 2026-08-29 판은 1,600편이다.
옛 문학은 제 종류의 프로파일만 갖고 현대 글의 기준이 되지 않는다. 모든 자료원은 재사용 조건을
명시하며 Git 커밋이나 위키의 옛 판 번호로 글자를 고정한다.

`scripts/fetchCorpus.py --refresh-manifest` 는 카탈로그의 조건으로 문서를 고르게 뽑아 판본과 해시를
`documents.json` 에 기록한다. 평소에는 아래 명령으로 이미 고정된 판을 받는다.

```powershell
.venv/Scripts/python.exe -X utf8 -B scripts/fetchCorpus.py
.venv/Scripts/python.exe -X utf8 -B scripts/fetchCorpus.py --check
```

수집기는 저장소 안에 원문이나 임시 압축 파일을 두지 않는다. 내려받는 동안 필요한 파일은 공통 실행
공간에 만들고 작업이 끝나면 지운다. 각 문서는 출처 주소와 라이선스를 외부 말뭉치의 `metadata.json` 에
함께 기록한다.

## 지문 표와 프로파일

`scripts/buildPrints.py` 는 말뭉치의 문장, 문단, 글을 한 행씩 Parquet 로 저장소 밖 `prints/` 에 둔다 (개발 extra
`corpus`). 탐침이 글을 다시 세지 않고 이것을 묻는다. `scripts/buildProfiles.py` 는 종류마다 문장 지표의 히스토그램과
백분위를 세어 `src/hanlint/data/profiles.json` 에 쓴다. 제품이 싣는 것은 이 파일뿐이고 규칙 outsideProfile 이 읽는다.

## 측정

규칙별 발화 수와 사람이 읽은 정탐률, 활용형 범위, 후보 채택률은
`tests/_attempts/corpus/` 에 기록한다. 카탈로그는 자료원이 무엇을 주는지만 소유하고 측정 결과를
복사하지 않는다.
