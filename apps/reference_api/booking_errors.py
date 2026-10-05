"""Stable service errors shared without importing the repository implementation."""


class RepositoryNotFound(LookupError):
    """A requested visible reference object does not exist."""


class InvalidWorkflowState(ValueError):
    """An append-only workflow transition is not permitted."""


class InvalidCatalogueValue(InvalidWorkflowState):
    """A request names a missing or inactive governed catalogue value."""


class IdempotencyKeyConflict(InvalidWorkflowState):
    """A tenant reuses an endpoint's key with a different payload."""
