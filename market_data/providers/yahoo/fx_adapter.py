"""GBP per foreign unit; daily bars and exact closed-bar research cut snapshots.

Snapshots are not WMR/official fixings. A 15:55 five-minute bar closes at 16:00;
the bar starting at 16:00 would introduce five minutes of look-ahead.
"""
from dataclasses import dataclass
from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal,InvalidOperation,localcontext
from zoneinfo import ZoneInfo

CUTS={'UK':'Europe/London','US':'America/New_York'}

@dataclass(frozen=True)
class FXPoint:
    label:str
    market_date:date
    source_at:datetime
    observed_at:datetime
    value:Decimal

def parse_fx(payload,*,symbol,start,end,received_at,interval):
    if interval not in {'1d','5m','1h'} or end<start or received_at.utcoffset() is None:
        raise ValueError('Invalid FX interval, dates or receipt')
    try:
        result=payload['chart']['result']
        if payload['chart'].get('error') or len(result)!=1:raise ValueError('Source did not return one FX chart')
        r=result[0];meta=r['meta']
        # Yahoo's daily USD/GBP endpoint can return its canonical GBP=X alias.
        # Admit only this observed alias with an explicit matching pair name;
        # quote currency alone cannot prove direction.
        identity=(meta['symbol']==symbol or (symbol=='USDGBP=X' and meta['symbol']=='GBP=X' and meta.get('longName')=='USD/GBP'))
        if (symbol not in {'EURGBP=X','USDGBP=X'} or not identity or meta['currency']!='GBP'
            or meta['instrumentType']!='CURRENCY' or meta['exchangeName']!='CCY'
            or meta['exchangeTimezoneName']!='Europe/London' or meta['dataGranularity']!=interval):
            raise ValueError('FX source identity does not match direction, currency, type, timezone or interval')
        timestamps=r.get('timestamp',[]);values=r['indicators']['quote'][0]['close']
        if len(timestamps)!=len(values) or len(set(timestamps))!=len(timestamps):raise ValueError('Invalid FX source columns')
        bars={};rejected=[];points=[]
        for ts,value in zip(timestamps,values):
            if isinstance(ts,bool) or not isinstance(ts,int):raise ValueError('Invalid FX timestamp')
            source=datetime.fromtimestamp(ts,timezone.utc)
            try:
                with localcontext() as ctx:
                    ctx.prec=40
                    number=Decimal(str(value)) if not isinstance(value,bool) else Decimal('NaN')
                    if not number.is_finite() or not 0<number<Decimal('1e18'):continue
                    number=number.quantize(Decimal('0.000000000001'))
                    if number<=0:continue
            except (InvalidOperation,ValueError,TypeError):continue
            bars[source]=number
        if interval=='1d':
            seen=set()
            for source,value in sorted(bars.items()):
                day=source.astimezone(ZoneInfo('Europe/London')).date()
                if not start<=day<=end or day>=received_at.astimezone(ZoneInfo('Europe/London')).date():continue
                if day in seen:raise ValueError('Duplicate FX daily date')
                seen.add(day);points.append(FXPoint('EOD',day,source,source,value))
            for ts,value in zip(timestamps,values):
                day=datetime.fromtimestamp(ts,timezone.utc).astimezone(ZoneInfo('Europe/London')).date()
                if start<=day<=end and day not in seen:
                    rejected.append({'marketDate':day.isoformat(),'cutoff':'EOD','reason':'Missing or incomplete provider daily FX close'})
        else:
            for offset in range((end-start).days+1):
                day=start+timedelta(days=offset)
                if day.weekday()>4:continue
                for label,zone in CUTS.items():
                    target=datetime.combine(day,time(16),ZoneInfo(zone)).astimezone(timezone.utc)
                    source=target-timedelta(minutes=5 if interval=='5m' else 60)
                    if target<=received_at and source in bars:
                        points.append(FXPoint(label,day,source,target,bars[source]))
                    else:rejected.append({'marketDate':day.isoformat(),'cutoff':label,'reason':f'Exact completed {interval} cutoff bar unavailable; no carry-forward'})
        return points,rejected
    except (KeyError,IndexError,TypeError,OverflowError) as exc:
        raise ValueError('Malformed Yahoo FX chart') from exc
