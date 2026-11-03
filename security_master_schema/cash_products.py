"""Cash security identity is separate from the common quotation arithmetic."""
ETP_KINDS=frozenset({'ETF','ETC','ETN','ETV','ETI'})
QUOTED_WRAPPERS=frozenset({'ETC','ETN','ETV','ETI','EXCHANGE_TRADED_VEHICLE','EXCHANGE_TRADED_CERTIFICATE'})
RATIO_SECURITIES=QUOTED_WRAPPERS|{'EQUITY','ETF'}
CASH_TYPES=RATIO_SECURITIES|{'ETP','FUND','FUND_SHARE_CLASS','DIGITAL_ASSET'}


def canonical_cash_unit(product,unit):
    """Old cash tickets called every asset SHARES; counts are unchanged."""
    return 'UNITS' if product in QUOTED_WRAPPERS|{'DIGITAL_ASSET','FUND'} and unit in ('SHARES','UNITS') else unit


def cash_product_basis(type_code,terms,day,frozen=None):
    """Resolve generic ETP only from its effective terms, never an ETF default.

    Original concrete definitions need no wrapper terms to establish their type.
    New generic bookings pin the exact term; old records require unambiguous
    effective history. This classifies, and never rescales quantity or price.
    """
    frozen=frozen or {};term_id=None
    if type_code=='ETP':
        rows=[r for r in terms if r['effective_from']<=day and (r['effective_to'] is None or r['effective_to']>=day)
            and r['status'] in ('ACTIVE','VALIDATED','SUPERSEDED')]
        if frozen.get('etpTermsId'):rows=[r for r in rows if str(r['etp_terms_id'])==frozen['etpTermsId']]
        if len(rows)!=1 or rows[0]['etp_kind'] not in ETP_KINDS:
            raise ValueError('Unique effective approved concrete ETP terms required')
        type_code=rows[0]['etp_kind'];term_id=rows[0]['etp_terms_id']
    if type_code=='FUND_SHARE_CLASS':type_code='FUND'
    if frozen.get('productBasis') is not None and frozen['productBasis']!=type_code:
        raise ValueError('Frozen cash product differs from original definition/terms')
    return type_code,term_id
