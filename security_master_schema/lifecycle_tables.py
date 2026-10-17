"""Append-only lifecycle policy, prepared inputs and posting audit."""
from sqlalchemy import Table,Column,String,Integer,DateTime,ForeignKey,CheckConstraint,text,Index
from sqlalchemy.dialects.postgresql import UUID,JSONB


def register(metadata,prefix='bond_redemption'):
    def uid(name,target=None,**kw): return Column(name,UUID(as_uuid=True),*([ForeignKey(target)] if target else []),**kw)
    policy=Table(prefix+'_policy',metadata,
        uid('tenant_id','ten.tenant.tenant_id',primary_key=True),uid('strategy_id','trd.strategy.strategy_id',primary_key=True),
        Column('revision',Integer,primary_key=True),Column('mode',String(20),nullable=False),Column('reason',String(2000),nullable=False),
        uid('actor_id','secm.user_account.user_account_id',nullable=False),uid('real_operator_id','secm.user_account.user_account_id',nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('now()')),
        *([uid('pricing_policy_id','ten.valuation_policy.valuation_policy_id',nullable=False),
           uid('pricing_cut_id','md.valuation_cut.valuation_cut_id',nullable=False)] if prefix=='fx_maturity' else []),
        CheckConstraint("revision>0 AND mode IN ('DIRECT','REVIEW','MANUAL')",name='ck_'+prefix+'_policy'),schema='trd')
    proposal=Table(prefix+'_proposal',metadata,
        uid('proposal_id',primary_key=True,server_default=text('uuidv7()')),
        uid('tenant_id','ten.tenant.tenant_id',nullable=False),uid('strategy_id','trd.strategy.strategy_id',nullable=False),
        uid('instrument_id','secm.instrument.instrument_node_id',nullable=False),
        Column('input_hash',String(64),nullable=False),Column('inputs',JSONB,nullable=False),
        Column('policy_revision',Integer,nullable=False),Column('mode',String(20),nullable=False),
        uid('prepared_by','secm.user_account.user_account_id',nullable=False),uid('prepared_operator','secm.user_account.user_account_id',nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('now()')),schema='trd')
    posting=Table(prefix+'_posting',metadata,
        uid('posting_id',primary_key=True,server_default=text('uuidv7()')),
        uid('tenant_id','ten.tenant.tenant_id',nullable=False),uid('strategy_id','trd.strategy.strategy_id',nullable=False),
        uid('proposal_id','trd.'+prefix+'_proposal.proposal_id',nullable=True),
        Column('request_key',String(255),nullable=False),Column('request_hash',String(64),nullable=False),
        Column('evidence',JSONB,nullable=False),Column('trade_ids',JSONB,nullable=False),
        uid('actor_id','secm.user_account.user_account_id',nullable=False),uid('real_operator_id','secm.user_account.user_account_id',nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('now()')),schema='trd')
    Index('uq_'+prefix+'_request' if prefix!='bond_redemption' else 'uq_redemption_request',posting.c.tenant_id,posting.c.request_key,unique=True)
    return policy,proposal,posting
