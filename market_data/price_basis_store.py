"""Append-only trusted ingestion boundary for observation/vintage-specific proof.

Not a tenant-editable certification API. Only assessed source evidence may call
this function; provider payloads cannot self-assert a complete adjustment history.
"""
from datetime import date
from sqlalchemy import select
from security_master_schema import models as m
from valuation.economics import evidence_hash
from .price_basis import normalise_as_traded


def record_price_basis_proof(c, observation_id, proof, recorded_at):
    if recorded_at.utcoffset() is None:
        raise ValueError('Proof timestamp requires timezone')
    row = c.execute(select(m.market_data_observation).where(
        m.market_data_observation.c.market_data_observation_id==observation_id).with_for_update()).mappings().one()
    if (recorded_at < row['received_at_utc'] or proof['marketDate'] != row['market_date'].isoformat()
            or date.fromisoformat(proof['anchorDate']) > recorded_at.date()):
        raise ValueError('Proof date/vintage does not match observation')
    normalise_as_traded(row['value'], row['value_basis'], proof, allow_split_conversion=True)
    digest = evidence_hash(proof)
    table = m.market_data_price_basis_proof
    prior = c.scalar(select(table.c.proof_id).where(table.c.observation_id==observation_id,table.c.proof_hash==digest))
    if prior: return prior
    return c.scalar(table.insert().values(observation_id=observation_id,proof_json=proof,
        proof_hash=digest,recorded_at_utc=recorded_at).returning(table.c.proof_id))


def load_price_basis_proof(c, observation_id, information_cutoff):
    table = m.market_data_price_basis_proof
    row = c.execute(select(table).where(table.c.observation_id==observation_id,
        table.c.recorded_at_utc<=information_cutoff).order_by(table.c.recorded_at_utc.desc(),table.c.proof_id.desc()).limit(1)).mappings().one_or_none()
    if not row: return None
    return dict(row['proof_json'], proofId=str(row['proof_id']), proofHash=row['proof_hash'],
        recordedAtUtc=row['recorded_at_utc'].isoformat())
