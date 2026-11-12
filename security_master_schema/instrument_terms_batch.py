"""Chunked, tenant-visible source graph for one contractual read.

The renderer never falls back to SQL. A source failure is handled per root by
its caller; missing/private references are retained as unknown, never filtered
out of a rendered contract. There is no process or cross-transaction cache.
"""
from collections import defaultdict
from sqlalchemy import select
from . import models as m
from .reference_visibility import visible_clause
from .errors import RepositoryNotFound

ID_BATCH_SIZE=500
REFERENCE_KEYS={'component_reference_node_id','underlying_reference_node_id','target_reference_node_id','reference_node_id','owner_reference_node_id'}
SCHEDULE_KEYS={'schedule_id','payment_schedule_id','observation_schedule_id'}
EVENT_KEYS={'schedule_event_id','observation_event_id'}


def id_chunks(identities):
    values=sorted(set(identities)-{None},key=str)
    for offset in range(0,len(values),ID_BATCH_SIZE):yield values[offset:offset+ID_BATCH_SIZE]


def source_links(facts):
    schedules,events,references=set(),set(),set()
    for entries in facts.values():
        for row in entries:
            for key,value in row.items():
                if value is None:continue
                if key in SCHEDULE_KEYS:schedules.add(value)
                if key in EVENT_KEYS:events.add(value)
                if key in REFERENCE_KEYS:references.add(value)
    return schedules,events,references


class TermsScheduleBatch:
    def __init__(self,connection,tenant,root_ids=()):
        self.connection,self.tenant=connection,tenant
        self.transaction=connection.get_transaction()
        self.roots=set(root_ids)
        self._data=defaultdict(dict);self._queried=defaultdict(set);self._indexes={}
        frontier=set(self.roots);visited=set()
        # This is a prefetch bound, not permission to render deeper chains.
        # Per-root rendering independently enforces the existing depth/cycle rule.
        for depth in range(4):
            current=frontier-visited
            if not current:break
            visited.update(current)
            frontier=self._load_wave(current,depth)

    def require_scope(self,connection,tenant):
        if connection is not self.connection or tenant!=self.tenant or connection.get_transaction() is not self.transaction:
            raise ValueError('Terms source batch belongs to a different read scope.')

    @staticmethod
    def _key(table,row):return tuple(row[column.name] for column in table.primary_key.columns)

    def _fetch(self,table,column,identities,extra=None):
        """One stable predicate per table/lookup column, in bounded ID chunks."""
        self.require_scope(self.connection,self.tenant)
        pending=set(identities)-{None}-self._queried[(table.fullname,column.name)]
        for chunk in id_chunks(pending):
            statement=select(table).where(column.in_(chunk)).order_by(*table.primary_key.columns)
            if extra is not None:statement=statement.where(extra)
            for record in self.connection.execute(statement).mappings():
                row=dict(record);self._data[table.fullname][self._key(table,row)]=row
            self._queried[(table.fullname,column.name)].update(chunk)
        if pending:
            self._indexes={key:value for key,value in self._indexes.items() if key[0]!=table.fullname}

    def rows(self,table,column,identities):
        """Database PK order is retained when merging rows from ID chunks."""
        name=column if isinstance(column,str) else column.name
        index_key=(table.fullname,name)
        if index_key not in self._indexes:
            grouped=defaultdict(list)
            for key,row in sorted(self._data[table.fullname].items()):grouped[row[name]].append(row)
            self._indexes[index_key]=grouped
        selected={}
        for identity in set(identities)-{None}:
            for row in self._indexes[index_key].get(identity,[]):selected[self._key(table,row)]=row
        return [row for key,row in sorted(selected.items())]

    def value(self,table,identity,column):
        rows=self.rows(table,next(iter(table.primary_key.columns)),[identity])
        return rows[0][column] if rows else None

    def _visible_nodes(self,identities):
        node=m.financial_reference_node
        self._fetch(node,node.c.reference_node_id,identities,(node.c.status=='ACTIVE')&visible_clause(node.c.reference_node_id,self.tenant))
        present=self.rows(node,node.c.reference_node_id,identities)
        self._fetch(m.reference_node_type,m.reference_node_type.c.reference_node_type_id,[r['reference_node_type_id'] for r in present])
        return {row['reference_node_id'] for row in present}

    def visible(self,identity):
        rows=self.rows(m.financial_reference_node,'reference_node_id',[identity])
        if not rows:raise RepositoryNotFound('Active visible reference was not found.')
        return rows[0]

    def parts(self,node_id,definition,kind):
        """Raw source facts, preserving the original reader's exact field set."""
        owners={node_id};dependencies=[];facts={}
        if kind=='SWAP':
            generic=self.rows(m.swap_definition_version,'instrument_definition_version_id',[definition['instrument_definition_version_id']])
            economics=generic[0]['economics_payload'] if generic else {}
            facts['swapTerms']=self.rows(m.swap_terms,'instrument_node_id',[node_id])
            facts['swapLegs']=self.rows(m.swap_leg,'swap_instrument_node_id',[node_id])
            dependencies=[(row['reference_node_id'],'Swap performance reference') for row in facts['swapLegs'] if row['reference_node_id'] and row['leg_role']=='PERFORMANCE']
        else:
            terms=self.rows(m.structured_product_terms,'instrument_node_id',[node_id])
            if len(terms)!=1:raise RepositoryNotFound('Current validated structured terms unavailable.')
            t=terms[0]['structured_product_terms_id'];economics=terms[0]
            for key,table in [('initialFixings',m.structured_product_initial_fixing),('conditions',m.structured_product_condition_group),('couponProgrammes',m.structured_product_coupon_programme),('rangeAccrual',m.structured_product_range_accrual_terms),('supertracker',m.structured_product_supertracker_terms)]:
                facts[key]=self.rows(table,'structured_product_terms_id',[t])
            facts['composition']=self.rows(m.instrument_composition,'structured_product_terms_id',[t])
            owners.update(row['component_reference_node_id'] for row in facts['composition'])
            facts['componentTerms']=self.rows(m.structured_product_component_terms,'instrument_composition_id',[row['instrument_composition_id'] for row in facts['composition']])
            facts['optionTerms']=self.rows(m.option_terms,'instrument_node_id',owners)
            groups=[row['condition_group_id'] for row in facts['conditions']]
            facts['barriers']=self.rows(m.barrier_rule,'condition_group_id',groups)
            facts['actions']=self.rows(m.condition_group_action,'condition_group_id',groups)
            facts['couponPeriods']=self.rows(m.structured_product_coupon_period,'coupon_programme_id',[row['coupon_programme_id'] for row in facts['couponProgrammes']])
            wrapper=self.rows(m.structured_product_wrapper_terms,'structured_product_terms_id',[t])
            if wrapper:
                economics={**economics,**wrapper[0]['note_inputs_json'],'transferTerms':wrapper[0]['transfer_terms_json']}
                dependencies.append((wrapper[0]['preference_share_instrument_id'],'Linked preference share'))
            share=self.rows(m.preference_share_terms,'structured_product_terms_id',[t])
            if share:
                economics={**economics,**share[0]['inputs_json']};pref_id=share[0]['preference_share_terms_id']
                facts['shareCalls']=self.rows(m.preference_share_redemption_period,'preference_share_terms_id',[pref_id])
                facts['terminalBranches']=self.rows(m.preference_share_terminal_branch,'preference_share_terms_id',[pref_id])
        return facts,economics,owners,dependencies

    def schedules(self,owners,facts):
        schedule_ids,event_ids,_=source_links(facts)
        schedule_ids.update(row['schedule_id'] for row in self.rows(m.schedule_event,'schedule_event_id',event_ids))
        records=self.rows(m.schedule,'owner_reference_node_id',owners)+self.rows(m.schedule,'schedule_id',schedule_ids)
        selected={self._key(m.schedule,row):row for row in records}
        return [row for key,row in sorted(selected.items())]

    def _load_wave(self,identities,depth):
        visible=self._visible_nodes(identities)
        nodes={node:self.visible(node) for node in visible}
        instruments={node for node,row in nodes.items() if depth==0 or self.value(m.reference_node_type,row['reference_node_type_id'],'type_code')=='INSTRUMENT'}
        d=m.instrument_definition_version
        self._fetch(d,d.c.instrument_node_id,instruments,d.c.is_current&(d.c.status=='APPROVED'))
        definitions={}
        for node in instruments:
            matches=self.rows(d,'instrument_node_id',[node])
            if len(matches)==1:definitions[node]=matches[0]
        self._fetch(m.instrument_type,m.instrument_type.c.instrument_type_id,[row['instrument_type_id'] for row in definitions.values()])
        kinds={node:self.value(m.instrument_type,row['instrument_type_id'],'type_code') for node,row in definitions.items()}
        swaps={node for node,kind in kinds.items() if kind=='SWAP'}
        notes={node for node,kind in kinds.items() if kind=='STRUCTURED_PRODUCT'}
        supported=swaps|notes
        self._fetch(m.organisation,m.organisation.c.organisation_id,[definitions[node]['issuer_organisation_id'] for node in supported])
        self._fetch(m.currency,m.currency.c.currency_id,[definitions[node]['base_currency_id'] for node in supported])
        self._fetch(m.instrument_dates,m.instrument_dates.c.instrument_node_id,supported)
        self._fetch(m.swap_definition_version,m.swap_definition_version.c.instrument_definition_version_id,[definitions[node]['instrument_definition_version_id'] for node in swaps])
        self._fetch(m.swap_terms,m.swap_terms.c.instrument_node_id,swaps)
        self._fetch(m.swap_leg,m.swap_leg.c.swap_instrument_node_id,swaps)
        t=m.structured_product_terms
        self._fetch(t,t.c.instrument_node_id,notes,t.c.is_current&t.c.status.in_(['ACTIVE','VALIDATED']))
        terms=[]
        for node in notes:
            matches=self.rows(t,'instrument_node_id',[node])
            if len(matches)==1:terms.append(matches[0])
        term_ids={row['structured_product_terms_id'] for row in terms}
        for table in (m.structured_product_initial_fixing,m.structured_product_condition_group,m.structured_product_coupon_programme,m.structured_product_range_accrual_terms,m.structured_product_supertracker_terms,m.instrument_composition,m.structured_product_wrapper_terms,m.preference_share_terms):
            self._fetch(table,table.c.structured_product_terms_id,term_ids)
        composition=self.rows(m.instrument_composition,'structured_product_terms_id',term_ids)
        self._fetch(m.structured_product_component_terms,m.structured_product_component_terms.c.instrument_composition_id,[row['instrument_composition_id'] for row in composition])
        owners=supported|{row['component_reference_node_id'] for row in composition}
        visible_owners=self._visible_nodes(owners)
        self._fetch(m.option_terms,m.option_terms.c.instrument_node_id,visible_owners,m.option_terms.c.is_current&m.option_terms.c.status.in_(['ACTIVE','VALIDATED']))
        groups=self.rows(m.structured_product_condition_group,'structured_product_terms_id',term_ids)
        for table in (m.barrier_rule,m.condition_group_action):self._fetch(table,table.c.condition_group_id,[row['condition_group_id'] for row in groups])
        programmes=self.rows(m.structured_product_coupon_programme,'structured_product_terms_id',term_ids)
        self._fetch(m.structured_product_coupon_period,m.structured_product_coupon_period.c.coupon_programme_id,[row['coupon_programme_id'] for row in programmes])
        shares=self.rows(m.preference_share_terms,'structured_product_terms_id',term_ids)
        for table in (m.preference_share_redemption_period,m.preference_share_terminal_branch):self._fetch(table,table.c.preference_share_terms_id,[row['preference_share_terms_id'] for row in shares])
        parts={}
        for node in supported:
            try:parts[node]=self.parts(node,definitions[node],kinds[node])
            except RepositoryNotFound:pass  # Only this root will fail at rendering.
        schedules,events,references=set(),set(),set()
        for facts,economics,owned,dependencies in parts.values():
            ids,event_ids,refs=source_links(facts);schedules.update(ids);events.update(event_ids);references.update(refs)
        self._visible_nodes(references)
        self._fetch(m.schedule_event,m.schedule_event.c.schedule_event_id,events)
        schedules.update(row['schedule_id'] for row in self.rows(m.schedule_event,'schedule_event_id',events))
        self._fetch(m.schedule,m.schedule.c.owner_reference_node_id,visible_owners)
        self._fetch(m.schedule,m.schedule.c.schedule_id,schedules)
        relevant={}
        for facts,economics,owned,dependencies in parts.values():
            for row in self.schedules(owned,facts):relevant[row['schedule_id']]=row
        active_owners=self._visible_nodes({row['owner_reference_node_id'] for row in relevant.values()})
        self._fetch(m.schedule_event,m.schedule_event.c.schedule_id,[identity for identity,row in relevant.items() if row['owner_reference_node_id'] in active_owners])
        next_wave=set()
        for facts,economics,owned,dependencies in parts.values():
            _,_,refs=source_links(facts)
            required=refs|{row['owner_reference_node_id'] for row in self.schedules(owned,facts)}
            if all(self.rows(m.financial_reference_node,'reference_node_id',[node]) for node in required):
                next_wave.update(identity for identity,relation in dependencies)
        return next_wave
