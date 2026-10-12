"""One closing-price family, with an independent exchange designation.

Legacy OFFICIAL_CLOSE is read as CLOSE plus an official requirement. This
adapter preserves immutable policy rows and must not infer exchange authority
from the generic is_official flag (also used by NAVs and FX fixings).
"""
from sqlalchemy import and_


def close_type(series_type):
    return 'CLOSE' if series_type == 'OFFICIAL_CLOSE' else series_type


def requires_official(rule):
    return rule['series_type'] == 'OFFICIAL_CLOSE' or bool(rule.get('require_official_close', False))


def series_filter(series, rule):
    kind = close_type(rule['series_type'])
    condition = series.c.series_type == kind
    if requires_official(rule):
        condition = and_(condition, series.c.closing_method == 'EXCHANGE_OFFICIAL')
    return condition


def matches_definition(rule, row):
    return (close_type(row['series_type']) == close_type(rule.series_type)
            and (not rule.require_official_close or row['closing_method'] == 'EXCHANGE_OFFICIAL')
            and (rule.value_basis is None or row['value_basis'] == rule.value_basis))


def closing_evidence(rule, row=None):
    return dict(requireOfficialClose=requires_official(rule),
                closingMethod=row['closing_method'] if row and close_type(row['series_type']) == 'CLOSE' else None)
