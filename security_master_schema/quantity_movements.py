"""Frozen fund-unit movement semantics, independent of an import or HTTP API."""
from decimal import Decimal,InvalidOperation

KINDS=frozenset({'TRANSFER','REINVESTMENT'})


def movement_proof(snapshot,*,product,price,quantity,trade_type=None):
    data=(snapshot or {}).get('quantityMovement')
    if data is None:
        if trade_type in KINDS:raise ValueError('Typed quantity movement requires frozen evidence')
        return None
    try:
        if (type(data['schemaVersion']) is not int or data['schemaVersion']!=1 or data['kind'] not in KINDS or product not in ('FUND','FUND_SHARE_CLASS')
            or price!=0 or quantity==0 or Decimal(data['signedQuantity'])!=quantity
            or data['recognitionBasis']!='POLICY_DAY_END' or not data['reason'].strip()
            or (trade_type is not None and data['kind']!=trade_type)
            or data['incomeRecognition']!=('UNASSESSED' if data['kind']=='REINVESTMENT' else 'NOT_APPLICABLE')
            or (data['kind']=='REINVESTMENT' and quantity<0)):
            raise ValueError('Inconsistent frozen fund-unit movement')
    except (KeyError,TypeError,AttributeError,InvalidOperation) as exc:
        raise ValueError('Missing frozen fund-unit movement evidence') from exc
    return data
