"""Bounded tenant calendar publication and assignment contracts."""
from datetime import date, time, datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, model_validator

class CalendarException(BaseModel):
    date: date
    status: Literal['OPEN','CLOSED']
    reason: str = Field(min_length=1,max_length=500)
    source_reference: str = Field(alias='sourceReference',min_length=1,max_length=250)
    model_config=ConfigDict(populate_by_name=True,extra='forbid',str_strip_whitespace=True)

class CalendarPublish(BaseModel):
    calendar_code: str = Field(alias='calendarCode',min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_][A-Za-z0-9_.-]*$')
    display_name: str = Field(alias='displayName',min_length=1,max_length=250)
    purpose: Literal['VALUATION','DEALING','SETTLEMENT']
    timezone_name: str = Field(alias='timezoneName',min_length=1,max_length=100)
    decision_time: time = Field(alias='decisionTime')
    coverage_from: date = Field(alias='coverageFrom')
    coverage_to: date = Field(alias='coverageTo')
    mode: Literal['WEEKDAYS','ALL_OPEN','ANY_OPEN','EXPLICIT']
    weekdays: list[int] = Field(default_factory=lambda:[0,1,2,3,4],max_length=7)
    base_calendar_ids: list[UUID] = Field(default_factory=list,alias='baseCalendarIds',max_length=10)
    exceptions: list[CalendarException] = Field(default_factory=list,max_length=1100)
    source_reference: str = Field(alias='sourceReference',min_length=1,max_length=250)
    model_config=ConfigDict(populate_by_name=True,extra='forbid',str_strip_whitespace=True)

    @model_validator(mode='after')
    def valid_schedule(self):
        try: ZoneInfo(self.timezone_name)
        except (KeyError,ValueError): raise ValueError('Unknown IANA timezone')
        if self.decision_time.tzinfo or self.decision_time.microsecond: raise ValueError('Decision time must be a local whole-second time')
        if not 0 <= (self.coverage_to-self.coverage_from).days < 1100: raise ValueError('Coverage must contain 1–1100 dates')
        if self.coverage_from.year<1900 or self.coverage_to.year>2200: raise ValueError('Supported dates are 1900–2200')
        if len(set(self.weekdays))!=len(self.weekdays) or any(x<0 or x>6 for x in self.weekdays): raise ValueError('Weekdays must be unique Monday=0 through Sunday=6')
        if len(set(self.base_calendar_ids))!=len(self.base_calendar_ids): raise ValueError('Base calendars must be unique')
        if (self.mode in ('ALL_OPEN','ANY_OPEN')) != bool(self.base_calendar_ids): raise ValueError('Only combined schedules require base calendars')
        if len({e.date for e in self.exceptions})!=len(self.exceptions): raise ValueError('One exception per date')
        if any(not self.coverage_from<=e.date<=self.coverage_to for e in self.exceptions): raise ValueError('Exceptions must be within coverage')
        return self

class CalendarAssignmentCreate(BaseModel):
    calendar_id: UUID = Field(alias='calendarId')
    target_kind: Literal['STRATEGY','FUND_REFERENCE'] = Field(alias='targetKind')
    target_id: UUID = Field(alias='targetId')
    valid_from: date = Field(alias='validFrom')
    valid_to: date = Field(alias='validTo')
    reason: str = Field(min_length=1,max_length=500)
    model_config=ConfigDict(populate_by_name=True,extra='forbid',str_strip_whitespace=True)
    @model_validator(mode='after')
    def valid_dates(self):
        if self.valid_to<self.valid_from: raise ValueError('Assignment dates are reversed')
        return self

class CalendarView(BaseModel):
    calendarId: UUID
    calendarCode: str
    displayName: str
    purpose: str
    timezoneName: str
    versionNo: int | None
    coverageFrom: date | None
    coverageTo: date | None
    tenantOwned: bool
    createdByUserAccountId: UUID | None
    createdAtUtc: datetime | None
    configuration: CalendarPublish | None

class CalendarDayView(BaseModel):
    date: date
    status: Literal['OPEN','CLOSED','UNKNOWN']
    evidence: dict

class CalendarDaysView(BaseModel):
    calendarId: UUID
    days: list[CalendarDayView]

class CalendarAssignmentView(BaseModel):
    assignmentId: UUID
    calendarId: UUID
    targetKind: str
    targetId: UUID
    purpose: str
    validFrom: date
    validTo: date
    reason: str
    createdByUserAccountId: UUID
    createdAtUtc: datetime

class CalendarOption(BaseModel):
    id: UUID
    label: str

class CalendarOptions(BaseModel):
    canManage: bool
    calendars: list[CalendarView]
    strategies: list[CalendarOption]
    assignments: list[CalendarAssignmentView]
