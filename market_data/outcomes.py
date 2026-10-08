"""Delivery outcomes are independent of execution mode and calendar certification."""
from datetime import date,timedelta

TERMINAL = frozenset({'COMPLETE','PARTIAL','FAILED','BLOCKED','ABORTED'})


def delivery_outcome(report):
    useful = report.get('accepted',0) + report.get('duplicates',0) > 0
    return ('PARTIAL' if report.get('rejected',0) else 'COMPLETE') if useful else 'FAILED'


def job_outcome(states):
    if any(s not in TERMINAL for s in states):
        raise ValueError('Unknown terminal outcome')
    for state in ('ABORTED','BLOCKED'):
        if state in states:
            return state
    if not states or all(s=='FAILED' for s in states):
        return 'FAILED'
    return 'COMPLETE' if all(s=='COMPLETE' for s in states) else 'PARTIAL'


def exit_code(outcome):
    if outcome not in TERMINAL:
        raise ValueError('Unknown terminal outcome')
    return 0 if outcome=='COMPLETE' else 3 if outcome=='PARTIAL' else 1


def gap_windows(report,start,end):
    """Only retry dated missing-price rejections, never identity/access failures."""
    dates=set()
    for rejection in report.get('rejections',[]):
        if rejection.get('reason')!='Missing or malformed equity price':
            continue
        try:
            day=date.fromisoformat(rejection['marketDate'])
        except (KeyError,TypeError,ValueError):
            continue
        if start<=day<=end:
            dates.add(day)
    spans=[]
    for day in sorted(dates):
        if spans and day==spans[-1][1]+timedelta(days=1):
            spans[-1]=(spans[-1][0],day)
        else:
            spans.append((day,day))
    return spans
