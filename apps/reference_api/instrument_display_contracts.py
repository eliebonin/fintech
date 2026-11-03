"""Read-only naming metadata, deliberately separate from frozen economic DTOs."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field


class InstrumentIdentifierDisplayView(BaseModel):
    scheme:str
    value:str


class InstrumentDisplayView(BaseModel):
    instrument_id: str | None = Field(default=None, alias='instrumentId')
    primary_name:str=Field(alias='primaryName')
    identifier:InstrumentIdentifierDisplayView|None=None
    context:list[str]=Field(default_factory=list)
    instrument_type:str|None=Field(default=None,alias='instrumentType')
    instrument_type_label:str|None=Field(default=None,alias='instrumentTypeLabel')
    search_text:str=Field(alias='searchText')
    basis:Literal['CURRENT_ACCESSIBLE_METADATA']='CURRENT_ACCESSIBLE_METADATA'
    model_config=ConfigDict(populate_by_name=True)
