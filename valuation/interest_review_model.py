"""Informative local-currency diagnostics; never modifies the actual earned flow."""
from datetime import timedelta
from decimal import Decimal,localcontext


def covered_days(day,explicit_dates):
    """Monday usually covers Sat–Mon; explicit weekend rows take precedence.

    Holidays cannot be inferred from absence: the retained review must let Ops
    supply coverage explicitly. This default is labelled a convention, not proof.
    """
    if day.weekday()!=0:return 1
    count=1
    for offset in (1,2):
        if day-timedelta(days=offset) in explicit_dates:break
        count+=1
    return count


def benchmark(rows,current_day,current_covered_days):
    """Mean of known per-day amounts in the five preceding calendar days.

    A tuple is (posting/value date, exact earned flow, covered day count). The
    baseline ends before the current coverage interval, preventing its weekend
    from being compared against itself. Overlapping coverage is unassessed.
    """
    if not 1<=current_covered_days<=31:raise ValueError('Covered days must be 1–31')
    end=current_day-timedelta(days=current_covered_days)
    start=end-timedelta(days=4);values={};overlaps=set()
    with localcontext() as context:
        context.prec=32  # Informative ratios only; original earned amounts are untouched.
        for day,amount,count in rows:
            if day>=current_day:continue
            if not isinstance(amount,Decimal) or not amount.is_finite():raise ValueError('Exact finite daily amount required')
            if not 1<=count<=31:raise ValueError('Covered days must be 1–31')
            normalized=amount/Decimal(count)
            for offset in range(count):
                value_date=day-timedelta(days=offset)
                if not start<=value_date<=end:continue
                if value_date in values:overlaps.add(value_date)
                values[value_date]=normalized
        known={day:amount for day,amount in values.items() if day not in overlaps}
        missing=[start+timedelta(days=i) for i in range(5) if start+timedelta(days=i) not in known]
        mean=sum(known.values(),Decimal(0))/Decimal(len(known)) if known else None
    return dict(average=mean,coveredDays=len(known),requestedDays=5,startDate=start,endDate=end,
        missingDates=missing,overlappingDates=sorted(overlaps))


def review_warning(amount,count,baseline,threshold=Decimal('25')):
    if not isinstance(amount,Decimal) or not amount.is_finite():raise ValueError('Exact finite amount required')
    if not 1<=count<=31:raise ValueError('Covered days must be 1–31')
    with localcontext() as context:
        context.prec=32
        normalized=amount/Decimal(count);mean=baseline['average'];change=None
        if mean is None:status='NO_BASELINE'
        elif mean==0:status='IN_LINE' if normalized==0 else 'CHANGED_FROM_ZERO'
        else:
            change=(normalized-mean)/abs(mean)*Decimal(100)
            status='CHECK' if abs(change)>threshold else 'IN_LINE'
    return dict(status=status,normalizedDaily=normalized,changePercent=change,thresholdPercent=threshold,
        partialBaseline=baseline['coveredDays']<5,blocking=False)
