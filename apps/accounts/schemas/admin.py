from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from ninja import Schema
from ninja_extra.schemas import PaginatedResponseSchema
from pydantic import Field


class DashboardFilter(Schema):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    role: Optional[UUID] = None
    client: Optional[str] = None

class TimeSeriesDashboardFilter(DashboardFilter):
    first_date: Optional[date] = Field(default=None, description="First date window to slide through the graph")
    last_date: Optional[date] = Field(default=None, description="Last date window to slide through the graph")



# https://www.figma.com/design/gYKoLL5lKJZ7vXxNzk5ITI/1840-Global-Talent-Cloud?node-id=14020-7836&t=InpFJVdmIQSVJ0Tq-0
class ItemValueSchema(Schema):
    item: str
    value: str

class PhaseCountSchema(Schema):
    phase: str
    count: int

class StageCountSchema(Schema):
    stage_name: str
    count: int

class StageDaySchema(Schema):
    stage_name: str
    avg_days_spent: int|float

class PhaseDaySchema(Schema):
    phase: str
    avg_days_spent: int|float

class PhaseTimelineSchema(Schema):
    graph: List[PhaseDaySchema]
    days_to_hire: int|float

class PipelineDashboardSchema(Schema):
    avg_days_to_hire: int
    avg_days_to_hire_per_stage: int
    applicant_hire_ratio: int
    dropout_ratio: int

    applicant_per_phase: list[PhaseCountSchema]
    applicant_per_stage: list[StageCountSchema]
    phase_timeline: PhaseTimelineSchema

class JobCountSchema(Schema):
    job: str
    count: int

class ClientCountSchema(Schema):
    client: str
    count: int

class LocationCountSchema(Schema):
    location: str
    count: int
class DemographicCountSchema(Schema):
    demographics: str
    count: int


class ExperienceCountSchema(Schema):
    experience: str
    count: int

class WithdrawalReasonSchema(Schema):
    reason: str
    count: int

class WithdrawalReasonsSchema(Schema):
    graph: List[WithdrawalReasonSchema]
    count: int

class RecruiterCountSchema(Schema):
    recruiter: str
    count: int

class PaginatedRecruiterHireSchema(PaginatedResponseSchema[RecruiterCountSchema]):
    total_hires: int

class RecruitmentDashboardSchema(Schema):
    total_applicants: int
    avg_applicants_per_job: int|float
    avg_applicants_per_client: int|float
    avg_applicants_per_recruiter: int|float

class ApplicantDashboardSchema(Schema):
    best_applicant_by_job: List[JobCountSchema]
    worst_applicant_by_job: List[JobCountSchema]
    best_applicant_by_client: List[ClientCountSchema]
    worst_applicant_by_client: List[ClientCountSchema]
    application_by_location: List[LocationCountSchema]
    application_by_gender: List[DemographicCountSchema]
    application_by_experience: List[ExperienceCountSchema]
    # application_by_source: List[ItemValueSchema]
    withdrawal_reasons: WithdrawalReasonsSchema



class PlatformHealthDashboardSchema(Schema):
    active_clients: int # last 30 days
    active_users_daily_average: int
    active_users: int # last 7 days
    system_uptime_percentage: float
    avg_api_response_time: List[ItemValueSchema]
    avg_page_response_time: List[ItemValueSchema]



class ApplicationHiresGraphItemSchema(Schema):
    day: date
    applications: int
    hires: int

class StuckApplicationSchema(Schema):
    uid: UUID
    talent: str
    job: str
    client: str
    phase: str
    stage_name: str
    days_in_stage: int|float


class RecentHiresSchema(Schema):
    uid: UUID
    role: str
    talent: str
    hired_by: str


class ApplicationPipelineRatioSchema(Schema):
   first_stage : StageCountSchema
   second_stage: StageCountSchema
   ratio: int|float




