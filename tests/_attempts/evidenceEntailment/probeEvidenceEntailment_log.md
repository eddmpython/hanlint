# 사람 합의 근거 함의 평가기 탐침

날짜: 2026-08-31

## 물은 것

외부 평가기가 한국어 evidence excerpt와 atomic fact 사이를 `supported`, `contradicted`, `insufficient`로
얼마나 가르는가. 확신이 낮을 때 기권하는가. confidence가 높은 답부터 남기면 실제 오류가 줄어드는가.

## 자료와 계약

[KLUE-NLI v1.1 dev](https://github.com/KLUE-benchmark/KLUE)의 고정 판을 썼다. 저장소 commit은
`3efd98708a40ff49251fddde35453f8fbb11f536`이고 원본 JSON SHA256은
`0699db82be17766b26e199864e6260443e17ec6e91d1870e876419e388f245b1`이다. 이 데이터는
CC BY-SA 4.0이다.

KLUE-NLI는 가설 작성자 한 명과 독립 검토자 네 명의 표에서 세 표 이상을 gold로 삼는다. 이번 평가판은
합의 기준을 네 표로 높였다. 여섯 source와 세 label에서 GUID SHA256 순으로 두 사례씩 골랐다. 전제와
가설은 평가판 전체에서 겹치지 않는다. 36개 평가판 content SHA256은
`864e8af5bb88e16521e630c9f8987b32b36916c1042fee6a8ee54e76d7d8f5d8`이다.

`entailment cases`가 낸 입력에는 gold, 원본 label과 다섯 표가 없다. manifest 파일 SHA256은
`d4eac74d54d39cb986564df607ec9018c519eb1b77f69d74af362aba4c6a55ed`이고 prompt SHA256은
`29b37f19ca35f418c77e6ed2ac1077ae4dd89a89982052165ef719e2b76a35f2`이다.

## 실행

- Ollama 0.23.2
- 모델 `qwen3:8b`
- 모델 digest `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`
- `temperature=0`, `seed=42`, `num_predict=4096`, thinking 끔
- prompt token 3,674개, 생성 token 900개
- 모델 원응답 SHA256 `41e68c458a07fbb1318c054894cdd1de2a3ba1f698726e29de348bba49f39677`
- 응답 봉투 content SHA256 `d5172db328d48f2ef9c71d8e3c8cf80d7281b3099a85d5863f4ac1067c1808c7`

## 결과

| 항목 | 값 |
|---|---:|
| 전체 사례 | 36 |
| 응답 | 36 |
| 기권 | 0 |
| 정답 | 25 |
| 선택 정확도 | 0.6944 |
| selective risk | 0.3056 |
| macro F1 | 0.6856 |

| gold label | precision | recall | F1 |
|---|---:|---:|---:|
| supported | 0.6471 | 0.9167 | 0.7586 |
| contradicted | 0.6667 | 0.6667 | 0.6667 |
| insufficient | 0.8571 | 0.5000 | 0.6316 |

confidence 1.0인 29개 가운데 10개가 틀렸다. 이 구간의 selective risk는 0.3448이었다. confidence
0.5인 일곱 개까지 모두 받으면 오류는 하나만 늘었고 전체 risk는 0.3056으로 내려갔다. 따라서 이 실행의
confidence는 오류를 앞에서 거르지 못했다. 기권도 한 번도 쓰지 않았다.

제품 result SHA256은 `6f4c7edb9f90872ad558a22546fa636973f896caa336d47511132c42244af2c2`다. 집계 파일 SHA256은
`65fa752651cb29768de3993be7328d8be16eafd2832401f984d79a0004fb4ea7`이다.

## 경계와 다음 목표

이 결과만으로 함의 평가기가 안전하다고 입증할 수 없다. 공개 KLUE가 모델 학습에 들어갔는지 알 수 없고 사례도
36개뿐이다. NLI 문장 관계를 재므로 출처와 fact의 현실 진실도 판정하지 않는다. 자기보고 confidence를
근거 원장의 자동 승인에 쓰면 안 된다는 반례만 얻었다.

다음 작법 목표는 의미 평가기를 더 키우는 일이 아니다. 같은 사실 계약으로 만든 글을 분야별 사람 평가자가
블라인드 대조하고 자연스러움, 독자 과업과 목소리를 따로 고르는 평가판을 만드는 일이다. 모델 자기평가와
문체 분포는 사람 선호를 대신하지 않는다.
