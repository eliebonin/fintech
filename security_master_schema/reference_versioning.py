"""Pure effective-date selection for canonical definition versions."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


class VersioningError(ValueError):
    """Raised when effective canonical versions are ambiguous or invalid."""


@dataclass(frozen=True)
class DefinitionVersion:
    version_id: UUID
    node_id: UUID
    sequence_no: int
    effective_from: date
    effective_to: date | None
    status: str


def select_current_version(
    versions: tuple[DefinitionVersion, ...],
    *,
    as_of_date: date,
) -> DefinitionVersion:
    """Select one approved version effective on a date; never choose ambiguously."""

    effective = tuple(
        version
        for version in versions
        if version.status == "APPROVED"
        and version.effective_from <= as_of_date
        and (version.effective_to is None or as_of_date <= version.effective_to)
    )
    if len(effective) != 1:
        raise VersioningError("Expected exactly one approved canonical definition version")
    return effective[0]
