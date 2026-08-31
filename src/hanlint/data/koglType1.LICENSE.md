# 국립국어원 파생 데이터 라이선스 (공공누리 제1유형)

아래 두 파일은 국립국어원이 공공누리 제1유형 (출처 표시) 으로 공개한 자료에서 왔다. 나머지 hanlint
코드와 데이터의 MIT 와는 별개다.

## `learningVocabulary.tsv`

- 원저작자: 국립국어원
- 자료: 한국어 학습용 어휘 목록 (5,965개)
- 원본: <https://www.korean.go.kr/front/etcData/etcDataView.do?etc_seq=70&mn_id=46&pageIndex=9>
- 받은 날: 2026-08-30
- 라이선스: [공공누리 제1유형 출처 표시](https://www.kogl.or.kr/info/licenseType1.do)
- 변경: cp949 를 UTF-8 로 옮기고 열 이름을 바꿨다. 낱말, 품사, 풀이, 등급의 내용은 바꾸지 않았다.
  만드는 절차와 원본 필드는 `learningVocabularySource.toml` 이 소유한다.

## `easyWords.toml`

- 원저작자: 국립국어원
- 자료: 다듬은 말 (<https://www.korean.go.kr/front/imprv/refineList.do>) 과 표준국어대사전
  (<https://stdict.korean.go.kr>) 의 동의어 정보
- 라이선스: [공공누리 제1유형 출처 표시](https://www.kogl.or.kr/info/licenseType1.do)
- 변경: 어려운 낱말과 쉬운 말의 짝만 뽑아 TOML 로 옮겼다.

공공누리 제1유형은 출처를 밝히면 상업적 이용과 변형을 포함해 자유롭게 쓸 수 있다. 이 파일이 그
출처 표시다.
