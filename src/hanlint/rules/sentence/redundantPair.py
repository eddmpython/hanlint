from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("redundantPair")
def redundantPair(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """역전 앞, 그때 당시, 매 시간마다 같은 겹말.

    왜: 뜻이 같은 두 말을 겹쳐 쓴 것이라 한 쪽이 군더더기다.
    어디서: 국립국어원 새국어생활 2005 한규희 겹말은 가능한 한 줄이자, 법조신문 넘쳐나는 겹말들.
        사전은 data/redundantPair.toml.
    고치기: 하나만 남긴다. 역전 앞 은 역 앞, 그때 당시 는 그때.
    안 잡는 것: 뜻을 강조하려고 일부러 겹친 말. 사전에 없는 겹말.
    """
    yield from dictionaryFindings(doc, "redundantPair", "redundantPair")
