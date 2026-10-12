"""Built-in trade recognition metadata, not tenant custom properties or settlement."""
from datetime import timezone
from .trade_properties import TradeFieldError

def recognition(request):
    execution=request.trade_datetime
    if execution.tzinfo is None or execution.utcoffset() is None:
        raise TradeFieldError('tradeDatetime','Execution must include a timezone offset.')
    default=execution.astimezone(timezone.utc).date()
    day=request.valuation_effective_date or default
    reason=(request.valuation_override_reason or '').strip() or None
    if day<default:
        raise TradeFieldError('valuationEffectiveDate','Valuation effective date cannot be before the UTC execution date.')
    if day!=default and not reason:
        raise TradeFieldError('valuationOverrideReason','A reason is required for a valuation-date override.')
    return dict(date=day.isoformat(),timezone='UTC',basis='EXPLICIT_OVERRIDE' if day!=default else 'UTC_TRADE_DATE',reason=reason)

def trade_values(request):
    from datetime import date
    value=recognition(request)
    return dict(valuation_effective_date=date.fromisoformat(value['date']),valuation_date_basis=value['basis'],valuation_override_reason=value['reason'])

def frozen_recognition(request):
    return {'valuationRecognition':recognition(request)}
