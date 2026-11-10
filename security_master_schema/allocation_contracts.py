"""Pure, tenant-neutral contracts for lifecycle annotation inheritance."""
from dataclasses import dataclass
from uuid import UUID
import json

@dataclass(frozen=True)
class FieldRule:
    definition_id: UUID
    behavior: str
    field_key: str | None = None
    source_definition_ids: tuple[UUID,...] = ()
    standard_field_key: str | None = None

    def __post_init__(self):
        if not isinstance(self.definition_id,UUID) or self.behavior not in {'ALLOCATION','INHERIT','INPUT'}:
            raise ValueError('Invalid allocation field rule')

@dataclass(frozen=True)
class AllocationPolicy:
    revision: int = 0
    fields: tuple[FieldRule,...] = ()
    configuration: dict | None = None

    def __post_init__(self):
        if self.revision<0 or len({r.definition_id for r in self.fields})!=len(self.fields):
            raise ValueError('Duplicate allocation fields or invalid revision')

    def payload(self):
        payload=dict(revision=self.revision,fields=[dict(definitionId=str(r.definition_id),behavior=r.behavior,**({'fieldKey':r.field_key} if r.field_key else {}))
            for r in sorted(self.fields,key=lambda r:str(r.definition_id))])
        if self.configuration:
            payload['profileVersionId']=str(self.configuration['profileVersionId'])
            payload['configurationHash']=self.configuration['configurationHash']
        return payload

@dataclass(frozen=True)
class AnnotationValue:
    value: str | bool
    record_id: UUID | None = None

    def __post_init__(self):
        if not isinstance(self.value,(str,bool)):
            raise ValueError('Annotation values must be canonical strings or booleans')

    def identity(self):
        # Version IDs preserve source evidence; stable record ID defines allocation.
        return json.dumps(dict(recordId=str(self.record_id)) if self.record_id else
                         dict(value=self.value),sort_keys=True,separators=(',',':'))
