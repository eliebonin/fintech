"""Timestamp validation used by pricing evidence; reconstruction lives in positions/."""
from datetime import datetime


def aware(value: datetime) -> None:
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Cutoffs and event times must be timezone aware')
