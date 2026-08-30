"""생성 전 요구를 결정적으로 검증하는 버전 고정 사실 계약."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from unicodedata import decimal, is_normalized
from urllib.parse import urlsplit

from .settings import PRESET_NAMES

BRIEF_VERSION = 1
EVIDENCE_BRIEF_VERSION = 2
BRIEF_VERSIONS = (BRIEF_VERSION, EVIDENCE_BRIEF_VERSION)
NUMBER_ATOM = re.compile(r"(?<!\d)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)*(?!\d)")
NUMBER_VALUE = re.compile(r"\d+(?:\.\d+)*")
FACT_ID = re.compile(r"F[1-9]\d*")
EVIDENCE_ID = re.compile(r"E[1-9]\d*")
SHA256_VALUE = re.compile(r"[0-9a-f]{64}")
CHECKED_AT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
REVIEW_STATUSES = ("unreviewed", "humanVerified")


def canonicalNumber(value: str) -> str:
    return "".join(str(decimal(character)) if character.isdecimal() else character for character in value if character != ",")


def numberValues(text: str) -> tuple[str, ...]:
    """올바른 천 단위 쉼표만 걷은 숫자 표면의 정렬된 집합."""
    return tuple(sorted({canonicalNumber(match.group(0)) for match in NUMBER_ATOM.finditer(text)}))


def checkedString(value: object, where: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{where} 는 양끝 공백 없는 문자열이다")
    if not is_normalized("NFC", value):
        raise ValueError(f"{where} 는 NFC 문자열이어야 한다")
    return value


def checkedStrings(value: object, where: str, allowEmpty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allowEmpty and not value):
        suffix = "배열이다" if allowEmpty else "비지 않은 문자열 배열이다"
        raise ValueError(f"{where} 는 {suffix}")
    found = tuple(checkedString(item, f"{where} {index}번째") for index, item in enumerate(value, start=1))
    if len(set(found)) != len(found):
        raise ValueError(f"{where} 에 같은 값이 두 번 있다")
    return found


@dataclass(frozen=True)
class AtomicFact:
    id: str
    statement: str

    def asDict(self) -> dict:
        return {"id": self.id, "statement": self.statement}


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    factIds: tuple[str, ...]
    sourceUrl: str
    revision: str | None
    checkedAt: str | None
    locator: str
    excerpt: str
    excerptSha256: str
    license: str
    reviewStatus: str

    def asDict(self) -> dict:
        return {
            "id": self.id,
            "factIds": list(self.factIds),
            "sourceUrl": self.sourceUrl,
            "revision": self.revision,
            "checkedAt": self.checkedAt,
            "locator": self.locator,
            "excerpt": self.excerpt,
            "excerptSha256": self.excerptSha256,
            "license": self.license,
            "reviewStatus": self.reviewStatus,
        }


@dataclass(frozen=True)
class WritingBrief:
    version: int
    preset: str
    reader: str
    task: str
    facts: tuple[AtomicFact, ...]
    mustInclude: tuple[str, ...]
    allowedNumbers: tuple[str, ...]
    forbidden: tuple[str, ...]
    minCharacters: int
    maxCharacters: int
    evidence: tuple[EvidenceRecord, ...] = ()

    @classmethod
    def fromMapping(cls, data: object) -> WritingBrief:
        if not isinstance(data, dict):
            raise ValueError("writing brief 는 JSON 객체다")
        baseKeys = {
            "version",
            "preset",
            "reader",
            "task",
            "facts",
            "mustInclude",
            "allowedNumbers",
            "forbidden",
            "length",
        }
        version = data.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version not in BRIEF_VERSIONS:
            raise ValueError(f"writing brief version 은 {', '.join(map(str, BRIEF_VERSIONS))} 가운데 하나다: {version}")
        expected = baseKeys | ({"evidence"} if version == EVIDENCE_BRIEF_VERSION else set())
        unknown = sorted(set(data) - expected)
        missing = sorted(expected - set(data))
        if unknown:
            raise ValueError(f"writing brief 의 모르는 키: {', '.join(unknown)}")
        if missing:
            raise ValueError(f"writing brief 의 빠진 키: {', '.join(missing)}")
        preset = checkedString(data["preset"], "preset")
        if preset not in PRESET_NAMES:
            raise ValueError(f"preset 은 {', '.join(PRESET_NAMES)} 가운데 하나다: {preset}")
        reader = checkedString(data["reader"], "reader")
        task = checkedString(data["task"], "task")
        facts = cls.factsFrom(data["facts"])
        evidence = cls.evidenceFrom(data["evidence"], facts) if version == EVIDENCE_BRIEF_VERSION else ()
        mustInclude = checkedStrings(data["mustInclude"], "mustInclude")
        forbidden = checkedStrings(data["forbidden"], "forbidden", allowEmpty=True)
        allowedNumbers = checkedStrings(data["allowedNumbers"], "allowedNumbers", allowEmpty=True)
        if any(not NUMBER_VALUE.fullmatch(value) for value in allowedNumbers):
            raise ValueError("allowedNumbers 는 숫자와 소수점만 든 문자열 배열이다")
        normalizedNumbers = tuple(sorted(allowedNumbers))
        if len(set(normalizedNumbers)) != len(normalizedNumbers):
            raise ValueError("allowedNumbers 에 정규화 뒤 같은 숫자가 두 번 있다")
        factText = "\n".join(fact.statement for fact in facts)
        contractText = "\n".join((reader, task, factText))
        contractNumbers = numberValues(contractText)
        if normalizedNumbers != contractNumbers:
            raise ValueError(
                "allowedNumbers 는 reader, task, facts 의 숫자 표면과 같아야 한다: "
                f"contract {list(contractNumbers)}, allowed {list(normalizedNumbers)}"
            )
        missingLiterals = [literal for literal in mustInclude if literal not in contractText]
        if missingLiterals:
            raise ValueError(f"mustInclude 는 reader, task, facts 안에 있어야 한다: {', '.join(missingLiterals)}")
        length = data["length"]
        if not isinstance(length, dict) or set(length) != {"min", "max"}:
            raise ValueError("length 는 min 과 max 정수만 든 객체다")
        minimum, maximum = length["min"], length["max"]
        if (
            isinstance(minimum, bool)
            or isinstance(maximum, bool)
            or not isinstance(minimum, int)
            or not isinstance(maximum, int)
            or minimum < 1
            or maximum < minimum
        ):
            raise ValueError("length 는 1 <= min <= max 인 정수다")
        return cls(
            version=version,
            preset=preset,
            reader=reader,
            task=task,
            facts=facts,
            mustInclude=mustInclude,
            allowedNumbers=normalizedNumbers,
            forbidden=forbidden,
            minCharacters=minimum,
            maxCharacters=maximum,
            evidence=evidence,
        )

    @staticmethod
    def factsFrom(value: object) -> tuple[AtomicFact, ...]:
        if not isinstance(value, list) or not value:
            raise ValueError("facts 는 비지 않은 원자 사실 배열이다")
        facts = []
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict) or set(item) != {"id", "statement"}:
                raise ValueError(f"facts {index}번째는 id 와 statement 만 든 객체다")
            identifier = checkedString(item["id"], f"facts {index}번째 id")
            if not FACT_ID.fullmatch(identifier):
                raise ValueError(f"facts {index}번째 id 는 F1 같은 꼴이다: {identifier}")
            facts.append(AtomicFact(identifier, checkedString(item["statement"], f"facts {index}번째 statement")))
        identifiers = [fact.id for fact in facts]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("facts 의 id 가 겹친다")
        return tuple(facts)

    @staticmethod
    def evidenceFrom(value: object, facts: tuple[AtomicFact, ...]) -> tuple[EvidenceRecord, ...]:
        if not isinstance(value, list) or not value:
            raise ValueError("evidence 는 비지 않은 근거 기록 배열이다")
        factIds = {fact.id for fact in facts}
        records = []
        for index, item in enumerate(value, start=1):
            where = f"evidence {index}번째"
            expected = {
                "id",
                "factIds",
                "sourceUrl",
                "revision",
                "checkedAt",
                "locator",
                "excerpt",
                "excerptSha256",
                "license",
                "reviewStatus",
            }
            if not isinstance(item, dict) or set(item) != expected:
                raise ValueError(f"{where}는 {', '.join(sorted(expected))}만 든 객체다")
            identifier = checkedString(item["id"], f"{where} id")
            if not EVIDENCE_ID.fullmatch(identifier):
                raise ValueError(f"{where} id는 E1 같은 꼴이다: {identifier}")
            linked = tuple(sorted(checkedStrings(item["factIds"], f"{where} factIds")))
            unknown = sorted(set(linked) - factIds)
            if unknown:
                raise ValueError(f"{where}가 없는 fact를 가리킨다: {', '.join(unknown)}")
            sourceUrl = checkedString(item["sourceUrl"], f"{where} sourceUrl")
            parsed = urlsplit(sourceUrl)
            if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError(f"{where} sourceUrl은 사용자 정보 없는 http 또는 https URL이다")
            revision = item["revision"]
            checkedAt = item["checkedAt"]
            if revision is not None:
                revision = checkedString(revision, f"{where} revision")
                if revision.casefold() in {"head", "latest", "main", "master"}:
                    raise ValueError(f"{where} revision은 움직이는 별칭이 아니라 고정 판이어야 한다")
            if checkedAt is not None:
                checkedAt = checkedString(checkedAt, f"{where} checkedAt")
                if not CHECKED_AT.fullmatch(checkedAt):
                    raise ValueError(f"{where} checkedAt은 YYYY-MM-DDTHH:MM:SSZ 꼴이다")
                try:
                    datetime.strptime(checkedAt, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError as error:
                    raise ValueError(f"{where} checkedAt은 실제 UTC 날짜와 시각이어야 한다") from error
            if revision is None and checkedAt is None:
                raise ValueError(f"{where}는 revision 또는 checkedAt으로 출처 판을 고정한다")
            excerpt = checkedString(item["excerpt"], f"{where} excerpt")
            if len(excerpt) > 1000:
                raise ValueError(f"{where} excerpt는 1,000자 이하다")
            excerptSha = checkedString(item["excerptSha256"], f"{where} excerptSha256")
            if not SHA256_VALUE.fullmatch(excerptSha) or sha256(excerpt.encode()).hexdigest() != excerptSha:
                raise ValueError(f"{where} excerptSha256가 excerpt와 다르다")
            licenseName = checkedString(item["license"], f"{where} license")
            reviewStatus = checkedString(item["reviewStatus"], f"{where} reviewStatus")
            if reviewStatus not in REVIEW_STATUSES:
                raise ValueError(f"{where} reviewStatus는 {', '.join(REVIEW_STATUSES)} 가운데 하나다")
            records.append(
                EvidenceRecord(
                    identifier,
                    linked,
                    sourceUrl,
                    revision,
                    checkedAt,
                    checkedString(item["locator"], f"{where} locator"),
                    excerpt,
                    excerptSha,
                    licenseName,
                    reviewStatus,
                )
            )
        identifiers = [record.id for record in records]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("evidence의 id가 겹친다")
        records.sort(key=lambda record: record.id)
        covered = {factId for record in records for factId in record.factIds}
        missing = sorted(factIds - covered)
        if missing:
            raise ValueError(f"근거 기록이 없는 fact다: {', '.join(missing)}")
        return tuple(records)

    @property
    def text(self) -> str:
        return "\n".join((self.reader, self.task, *(fact.statement for fact in self.facts)))

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.asDict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode()).hexdigest()

    def asDict(self) -> dict:
        data = {
            "version": self.version,
            "preset": self.preset,
            "reader": self.reader,
            "task": self.task,
            "facts": [fact.asDict() for fact in self.facts],
            "mustInclude": list(self.mustInclude),
            "allowedNumbers": list(self.allowedNumbers),
            "forbidden": list(self.forbidden),
            "length": {"min": self.minCharacters, "max": self.maxCharacters},
        }
        if self.version == EVIDENCE_BRIEF_VERSION:
            data["evidence"] = [record.asDict() for record in self.evidence]
        return data


def loadWritingBrief(path: str | Path) -> WritingBrief:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"writing brief JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error
    return WritingBrief.fromMapping(data)
