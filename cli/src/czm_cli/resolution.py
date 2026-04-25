from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .errors import ResolutionError


@dataclass(slots=True)
class ResolvedEntity:
    id: int
    display: str


def _normalize(text: str) -> str:
    return text.casefold()


def _score_matches(reference: str, candidates: Sequence[tuple[int, Sequence[str]]]) -> list[int]:
    ref = reference.strip()
    ref_norm = _normalize(ref)
    exact: list[int] = []
    case_insensitive: list[int] = []
    substring: list[int] = []
    for entity_id, fields in candidates:
        field_texts = [field for field in fields if field is not None]
        if any(field == ref for field in field_texts):
            exact.append(entity_id)
        elif any(_normalize(field) == ref_norm for field in field_texts):
            case_insensitive.append(entity_id)
        elif any(ref_norm in _normalize(field) for field in field_texts):
            substring.append(entity_id)
    if len(exact) == 1:
        return exact
    if len(exact) > 1:
        raise ResolutionError(f"reference {reference!r} is ambiguous")
    if len(case_insensitive) == 1:
        return case_insensitive
    if len(case_insensitive) > 1:
        raise ResolutionError(f"reference {reference!r} is ambiguous")
    if len(substring) == 1:
        return substring
    if len(substring) > 1:
        raise ResolutionError(f"reference {reference!r} is ambiguous")
    return []


def resolve_single(reference: str | int, candidates: Iterable[tuple[int, Sequence[str]]], *, label: str) -> int:
    candidate_list = list(candidates)
    if isinstance(reference, int):
        matches = [entity_id for entity_id, _ in candidate_list if entity_id == reference]
        if len(matches) == 1:
            return matches[0]
        raise ResolutionError(f"{label} {reference} was not found", exit_code=3)
    ref_text = str(reference).strip()
    if ref_text.isdigit():
        numeric = int(ref_text)
        matches = [entity_id for entity_id, _ in candidate_list if entity_id == numeric]
        if len(matches) == 1:
            return matches[0]
    matches = _score_matches(ref_text, candidate_list)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ResolutionError(f"{label} {reference!r} was not found", exit_code=3)
    raise ResolutionError(f"{label} {reference!r} is ambiguous")

