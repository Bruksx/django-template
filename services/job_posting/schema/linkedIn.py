from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List

from services.job_posting.enums.linkedIn import EmploymentStatusEnum, OperationTypeEnum, WorkPlaceTypeEnum


@dataclass
class AccessTokenSchema:
	token: str
	expires_in: datetime

@dataclass
class ValueSchema:
	amount: str
	currencyCode: str

@dataclass
class RangeValueSchema:
	start: ValueSchema
	end: ValueSchema

@dataclass
class CompensationSchema:
	period: str
	type: str
	value: ValueSchema|RangeValueSchema


@dataclass
class CompensationsSchema:
	compensations: List[CompensationSchema]

@dataclass
class JobSchema:
	companyApplyUrl: str
	companyApplyUrl: str
	description: str
	employmentStatus: EmploymentStatusEnum
	externalJobPostingId: str
	listedAt: int
	title: str
	location: str
	workplaceTypes: List[str]
	compensation: CompensationsSchema
	experienceLevel: str