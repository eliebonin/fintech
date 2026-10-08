"""Pure, three-state calendar composition; no implied reference coverage."""

def reference_day(session_status, holiday_name):
    if holiday_name:
        return 'UNKNOWN' if session_status in ('OPEN','HALF_DAY') else 'CLOSED'
    return 'OPEN' if session_status in ('OPEN','HALF_DAY') else 'CLOSED' if session_status=='CLOSED' else 'UNKNOWN'


def compose_day(day, mode, weekdays, components, exception):
    if exception:
        return {**exception,'components':components,'origin':'EXCEPTION'}
    states=list(components.values())
    if mode=='WEEKDAYS':
        status='OPEN' if day.weekday() in weekdays else 'CLOSED'
    elif mode=='ALL_OPEN':
        status='CLOSED' if 'CLOSED' in states else 'OPEN' if states and all(s=='OPEN' for s in states) else 'UNKNOWN'
    elif mode=='ANY_OPEN':
        status='OPEN' if 'OPEN' in states else 'CLOSED' if states and all(s=='CLOSED' for s in states) else 'UNKNOWN'
    else:
        status='UNKNOWN'
    return dict(status=status,reason=mode,components=components,origin='BASE_RULE')
