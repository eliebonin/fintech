"""Allocation-aware ledger view; default economic aggregation is unchanged."""
from dataclasses import dataclass,asdict,replace
from .contracts import PositionKey
from .equity import booking_key
from .reconstruction import reconstruct,digest

@dataclass(frozen=True)
class AllocatedPositionKey(PositionKey):
    allocation_signature: tuple[tuple[str,str],...]


def allocation_signature(policy, values):
    return tuple((rule.field_key or str(rule.definition_id),values[rule.definition_id].identity()
                  if rule.definition_id in values else 'null')
        for rule in sorted(policy.fields,key=lambda r:r.field_key or str(r.definition_id)) if rule.behavior=='ALLOCATION')


def reconstruct_allocations(facts,request,policy,annotations,*,splits=()):
    """Partition BEFORE replay/pruning, preserving cancellation and recognition rules."""
    def key(booking,tenant,strategy):
        base=booking_key(booking,tenant,strategy)
        return AllocatedPositionKey(**asdict(base),allocation_signature=allocation_signature(policy,annotations.get(booking.trade_id,{})))
    projection=reconstruct(facts,request,splits=splits,key_builder=key)
    # Ordinary reconstruction hashes ledger facts only. This view also binds all
    # visible source annotations and the selected policy, including inheritance.
    visible={f.trade_id for f in projection.facts}
    proof={str(t):{str(k):dict(value=v.value,recordId=str(v.record_id) if v.record_id else None)
                   for k,v in sorted(annotations.get(t,{}).items(),key=lambda p:str(p[0]))}
           for t in sorted(visible,key=str)}
    return replace(projection,input_hash=digest(dict(ledgerHash=projection.input_hash,
        policy=policy.payload(),annotations=proof)),engine_version='allocated-'+projection.engine_version)
