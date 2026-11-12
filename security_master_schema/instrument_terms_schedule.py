"""Read-only projection of current approved contractual facts, independent of booking."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel
from security_master_schema import models as m
from .errors import RepositoryNotFound


class TermsLayer(BaseModel):
    instrumentId: str
    canonicalName: str
    instrumentType: str
    relation: str
    version: int
    issuer: str | None
    currency: str | None
    dates: dict
    economics: dict
    facts: dict[str, list[dict]]


class TermsScheduleView(BaseModel):
    instrumentId: str
    basis: str = 'CURRENT_APPROVED_TERMS'
    layers: list[TermsLayer]
    referenceLabels: dict[str, str]


class TermsScheduleResponse(BaseModel):
    data: TermsScheduleView


def _display(value):
    # Monetary levels must never travel through a binary float.
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, (UUID, date, datetime)): return str(value)
    if isinstance(value, dict): return {k: _display(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_display(v) for v in value]
    return value

from .instrument_terms_batch import TermsScheduleBatch,REFERENCE_KEYS


def _project_terms(source,instrument_id):
    source.require_scope(source.connection,source.tenant)
    layers,labels,visited=[],{},set()
    def visible(identity):
        node=source.visible(identity);labels[str(identity)]=node['canonical_name'];return node
    def visit(node_id,relation,depth=0):
        if node_id in visited or depth>3:raise RepositoryNotFound('Contractual reference chain cannot be displayed.')
        visited.add(node_id);node=visible(node_id)
        if depth and source.value(m.reference_node_type,node['reference_node_type_id'],'type_code')!='INSTRUMENT':return
        definitions=source.rows(m.instrument_definition_version,'instrument_node_id',[node_id])
        if len(definitions)!=1:raise RepositoryNotFound('Current approved instrument terms unavailable.')
        definition=definitions[0];kind=source.value(m.instrument_type,definition['instrument_type_id'],'type_code')
        if kind not in {'SWAP','STRUCTURED_PRODUCT'}:
            if depth:return
            raise RepositoryNotFound('Terms and schedule are supported for structured products and swaps.')
        issuer=source.value(m.organisation,definition['issuer_organisation_id'],'legal_name')
        currency=source.value(m.currency,definition['base_currency_id'],'currency_code')
        dates=source.rows(m.instrument_dates,'instrument_node_id',[node_id])
        facts,economics,owners,dependencies=source.parts(node_id,definition,kind)
        # Preserve all source reference checks, including funding, condition
        # targets and schedule owners. An inaccessible dependency fails its root.
        if kind=='SWAP':
            for leg in facts['swapLegs']:
                if leg['reference_node_id']:visible(leg['reference_node_id'])
        for entries in facts.values():
            for row in entries:
                for key,value in row.items():
                    if value is not None and key in REFERENCE_KEYS:visible(value)
        schedules=source.schedules(owners,facts)
        for row in schedules:visible(row['owner_reference_node_id'])
        events=source.rows(m.schedule_event,'schedule_id',[row['schedule_id'] for row in schedules])
        events=sorted(events,key=lambda row:(row['event_date'],row['event_sequence'],str(row['schedule_event_id'])))
        purposes={row['schedule_id']:row['schedule_type'] for row in schedules}
        facts['scheduleEvents']=[dict(row,schedule_type=purposes[row['schedule_id']]) for row in events]
        layers.append(TermsLayer(instrumentId=str(node_id),canonicalName=node['canonical_name'],instrumentType=kind,relation=relation,version=definition['sequence_no'],issuer=issuer,currency=currency,dates=_display(dates[0] if dates else {}),economics=_display(economics),facts=_display(facts)))
        for identity,label in dependencies:visit(identity,label,depth+1)
    visit(instrument_id,'Selected instrument')
    return TermsScheduleView(instrumentId=str(instrument_id),layers=layers,referenceLabels=labels)


def load_terms_schedule(c,tenant,instrument_id,*,source=None):
    source=source if source is not None else TermsScheduleBatch(c,tenant,[instrument_id])
    source.require_scope(c,tenant)
    if instrument_id not in source.roots:raise ValueError('Instrument was not included in this read scope.')
    return _project_terms(source,instrument_id)


def load_terms_schedules(c,tenant,instrument_ids):
    source=TermsScheduleBatch(c,tenant,instrument_ids);result={}
    for identity in sorted(source.roots,key=str):
        try:result[identity]=load_terms_schedule(c,tenant,identity,source=source)
        except (RepositoryNotFound,ValueError):result[identity]=None
    return result
