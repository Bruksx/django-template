from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List
import xml.etree.ElementTree as ET

from services.job_posting.enums.linkedIn import EmploymentStatusEnum, OperationTypeEnum, WorkPlaceTypeEnum
from services.utils import dict_to_xml


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

	def to_xml(self)->ET.Element:
		job_elem = ET.Element("job")
		ET.SubElement(job_elem, "partnerJobId").text = self.externalJobPostingId
		ET.SubElement(job_elem, "title").text = self.title
		ET.SubElement(job_elem, "description").text = self.description
		ET.SubElement(job_elem, "location").text = self.location
		ET.SubElement(job_elem, "applyUrl").text = self.companyApplyUrl
		ET.SubElement(job_elem, "employmentStatus").text = self.employmentStatus
		ET.SubElement(job_elem, "experienceLevel").text = self.experienceLevel
		ET.SubElement(job_elem, "listedAt").text = str(self.listedAt)

		workplace_types = ET.SubElement(job_elem, "workplaceTypes")
		for wp in self.workplaceTypes:
			ET.SubElement(workplace_types, "workplaceType").text = wp

		compensation_elem = ET.SubElement(job_elem, "compensation")
		dict_to_xml(compensation_elem, self.compensation)
		return job_elem
