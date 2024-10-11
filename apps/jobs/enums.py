from core.enums import BaseEnum


class WorkStructureEnum(BaseEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    IN_OFFICE = "in office"


class TechnologicalRequirementsEnum(BaseEnum):
    WINDOWS = "windows"
    MACBOOK = "macbook"
    EITHER = "either"


class LunchBreakEnum(BaseEnum):
    PAID = "paid"
    UNPAID = "unpaid"


class QuestionTypeEnum(BaseEnum):
    SINGLE_SELECT = "single select"
    MULTI_SELECT = "multi select"
    TEXT = "text"
    FILE = "file"
    

class StageType(BaseEnum):
    SCREENING = "screening"
    INTERVIEW = "interview"
    INTERVIEW_2 = "interview 2"
    HIRED = "hired"
    ONBOARDING = "onboarding"
    REJECTED = "rejected"

class WithdrawalFeedbackType(BaseEnum):
    SKILLS = "Skills and/or Qualification Mismatch"
    JOB_OFFER = "Accepted Another Job Offer"
    WORK_HOURS = "Conflict with Work Hours"
    COMPENSATION = "Compensation"
    OTHERS = "Others"