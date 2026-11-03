"""Local preparation controls, never an assertion of RTS 22/schema acceptance."""
import csv
from io import StringIO
import hashlib
import json

MAPPED_FIELDS=('instrumentIsin','instrumentDescription','buyerId','sellerId','capacity','venueMic','investmentDecisionId','executionDecisionId')
SUPPORTED_FAMILIES=frozenset({'EQUITY','ETP','ETF','FUND','FUND_SHARE_CLASS','BOND',
    'ACTIVELY_MANAGED_CERTIFICATE','STRUCTURED_PRODUCT','STRUCTURED_NOTE','FUTURE',
    'OPTION','VANILLA_OPTION','SWAP','GENERIC_SWAP','FX_FORWARD'})

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def assess(facts,*,firm_scope,mapping,decision=None,disposition='AUTO',needs_reassessment=False):
    # A listing, ISIN, missing adapter or short maturity proves neither scope direction.
    proposal='NOT_REPORTABLE' if firm_scope=='OUT_OF_SCOPE' else 'NEEDS_ASSESSMENT'
    reportability='NEEDS_ASSESSMENT' if needs_reassessment else decision or proposal
    missing=[key for key in MAPPED_FIELDS if key not in {'instrumentIsin','instrumentDescription'} and not mapping.get(key)]
    if not mapping.get('instrumentIsin') and not mapping.get('instrumentDescription'):missing.append('instrumentIdentity')
    missing += [key for key in ('executionTime','quantity','quantityUnit','executionPrice','priceBasis','priceCurrency')
                if facts.get(key) is None or facts.get(key)=='']
    if not facts.get('bookingTerms'):missing.append('bookingTerms')
    if facts.get('referenceVisible') is False:missing.append('referenceAccess')
    if facts.get('instrumentType') not in SUPPORTED_FAMILIES:missing.append('productMapping')
    if facts.get('tradeType') not in {'INVESTMENT','SUBSCRIPTION','REDEMPTION'}:missing.append('eventMapping')
    if facts.get('lifecycleStatus')!='BOOKED':missing.append('lifecycleReview')
    if firm_scope=='UNASSESSED':missing.append('firmScope')
    if needs_reassessment:missing.append('sourceReassessment')
    if reportability=='NEEDS_ASSESSMENT':missing.append('reportabilityAssessment')
    ready=not missing and reportability=='REPORTABLE'
    return dict(reportability=reportability,proposedReportability=proposal,
        readiness='READY' if ready else 'INCOMPLETE',disposition=disposition,
        included=ready and disposition=='AUTO',missingFields=missing,validationLevel='PREPARATION_ONLY')

def preparation_csv(rows):
    """Exact decimal strings; formula-like labels are escaped for spreadsheets."""
    fields=('candidateId','revision','instrumentName','instrumentType','tradeType','executionTime',
        'quantity','quantityUnit','executionPrice','priceBasis','priceCurrency',*MAPPED_FIELDS)
    stream=StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    writer.writeheader()
    for row in rows:
        values={key:row.get(key) for key in ('candidateId','revision')}|row['facts']|row['mapping']
        safe={}
        for key in fields:
            value='' if values.get(key) is None else str(values[key])
            if key not in {'quantity','executionPrice','revision'} and value.lstrip().startswith(('=','+','-','@','\t','\r')):value="'"+value
            safe[key]=value
        writer.writerow(safe)
    return stream.getvalue()
