"""Invented, repeatable whole-swap MTM/unit fixtures. NOT a pricing model/feed.

Actual exchange sessions provide dates only. Index paths, dividends, funding
fixings and discounts are invented. No actual SPX/UKX/benchmark observations
are copied, and no quarterly resets/payments are implied by these examples.
"""
from datetime import date
from decimal import Decimal, localcontext
from hashlib import sha256

START=date(2024,10,15)
END=date(2026,10,14)
MATURITY=date(2027,10,15)
SPECS={
    'SPX':dict(units='100000',leverage='1',initial='5800',currency='USD',calendar='XNYS',
        spread='0.0015',dayCount='360',rateStart='0.0485',rateEnd='0.0355',
        annualDrift='0.08',dailyVol='0.01134',dividendYield='0.015'),
    'UKX':dict(units='25000',leverage='1.5',initial='8250',currency='GBP',calendar='XLON',
        spread='0.0010',dayCount='365',rateStart='0.0495',rateEnd='0.0380',
        annualDrift='0.06',dailyVol='0.00882',dividendYield='0.035'),
}


def build_history(code:str,*,leverage:Decimal|None=None)->dict:
    import exchange_calendars as calendars
    specification=SPECS[code]
    calendar=calendars.get_calendar(specification['calendar'],start=START.isoformat(),end=END.isoformat())
    sessions=calendar.sessions_in_range(START.isoformat(),END.isoformat())
    d=lambda field:Decimal(specification[field])
    with localcontext() as context:
        context.prec=48
        multiplier=leverage if leverage is not None else d('leverage')
        if not multiplier.is_finite() or multiplier<=0:raise ValueError('Positive finite leverage required')
        initial=d('initial');level=initial;funding_growth=Decimal(1);dividends=Decimal(0)
        prior=START;prices=[]
        for session in sessions:
            day=session.date();elapsed=Decimal((day-prior).days)
            fraction=Decimal((day-START).days)/Decimal((END-START).days)
            rate=d('rateStart')+(d('rateEnd')-d('rateStart'))*fraction
            if day!=START:
                # Hash-based sum of uniforms: stable across runs/Python versions.
                entropy=sha256(f'MOCK-UNIT-SWAP-V1:{code}:{day}'.encode()).digest()
                shock=sum((Decimal(int.from_bytes(entropy[i:i+2],'big'))/Decimal(65536) for i in range(0,24,2)),Decimal(0))-Decimal(6)
                level*=Decimal(1)+d('annualDrift')/Decimal(252)+d('dailyVol')*shock
                dividends+=initial*d('dividendYield')*elapsed/Decimal(365)
                funding_growth*=(Decimal(1)+(rate+d('spread'))/d('dayCount'))**int(elapsed)
            funding=initial*(funding_growth-Decimal(1))
            # Illustrative remaining-tenor discount only; not a calibrated DCF.
            discount=Decimal(1)/(Decimal(1)+rate*Decimal((MATURITY-day).days)/Decimal(365))
            mark=multiplier*(level-initial+dividends-funding)*discount
            prices.append(dict(date=day.isoformat(),observedAt=calendar.session_close(session).isoformat(),
                close=str(mark.quantize(Decimal('0.00000001'))),indexLevel=str(level.quantize(Decimal('0.00000001'))),
                assumedFundingRate=str(rate.quantize(Decimal('0.00000001')))))
            prior=day
    return dict(synthetic=True,code=code,specification=specification,effectiveDate=START.isoformat(),
        maturityDate=MATURITY.isoformat(),quote='WHOLE_SWAP_MTM_PER_UNIT',quoteFactor='1',
        sessionSource='exchange_calendars '+calendars.__version__+' '+specification['calendar'],
        methodology='Invented index path plus gross dividend carry minus compounded funding and spread; '
        'illustrative remaining-tenor discount; leverage applied once to whole-swap mark; no interim resets or payments. '
        'One unit is one currency unit per index point. Not actual market data or a production pricer.',prices=prices)
