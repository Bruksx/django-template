from core.enums import BaseEnum


class WorkStructureEnum(BaseEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    IN_OFFICE = "in office"


class TechnologicalRequirementsEnum(BaseEnum):
    WINDOWS = "windows"
    MACBOOK = "macbook"
    EITHER = "either mac or windows"


class LunchBreakEnum(BaseEnum):
    PAID = "paid"
    UNPAID = "unpaid"


class QuestionTypeEnum(BaseEnum):
    SINGLE_SELECT = "single select"
    MULTI_SELECT = "multi select"
    TEXT = "text"
    FILE = "file"
    

class PhaseType(BaseEnum):
    NEW = "new"
    SCREENING = "screening"
    INTERVIEW = "interview"
    ONBOARDING = "onboarding"
    HIRED = "hired"
    REJECTED = "rejected"

class WithdrawalFeedbackType(BaseEnum):
    SKILLS = "Skills and/or Qualification Mismatch"
    JOB_OFFER = "Accepted Another Job Offer"
    WORK_HOURS = "Conflict with Work Hours"
    COMPENSATION = "Compensation"
    OTHERS = "Others"

class JobStatusType(BaseEnum):
    DRAFT = "draft"
    PAUSED = "paused"
    POSTED = "posted"
    CLOSED = "closed"

class ActionType(BaseEnum):
    DRAFT = "draft"
    PAUSED = "paused"
    POSTED = "posted"
    CLOSED = "closed"
    DELETE = "delete"

class ScreeningResultStatusType(BaseEnum):
    PASS = "Pass"
    FAIL =  "Fail"

class UpdateQuickReviewType(BaseEnum):
    ADVANCE = "advance"
    REJECT = "reject"

class RejectionReasonType(BaseEnum):
    OTHERS = "Others"
    INSUFFICIENT_EXPERIENCE = "Insufficient Experience"
    SKILLS_MISMATCH = "Skills Mismatch"
    QUALIFICATION_MISMATCH = "Qualification Mismatch"
    LANGUAGE_SKILLS_MISMATCH = "Language Skills Mismatch"
    INDUSTRY_MISMATCH = "Industry Mismatch"
    SALARY_MISMATCH = "Salary Mismatch"
    LOCATION_WORK_AUTHORIZATION_MISMATCH = "Location/Work Authorization Mismatch"
    INCOMPLETE_PROFILE_APPLICATION = "Incomplete Profile/Application"
    POOR_INTERVIEW_PERFORMANCE = "Poor Interview Performance"
    TECHNICAL_ASSESSMENT_UNSUCCESSFUL = "Technical Assessment Unsuccessful"
    CULTURE_TEAM_FIT_MISMATCH = "Culture/Team Fit Mismatch"
    AVAILABILITY_MISMATCH = "Availability Mismatch"
    CAREER_GOALS_MISMATCH = "Career Goals Mismatch"
    STRONGER_CANDIDATE_SELECTED = "Stronger Candidate Selected"
    CANDIDATE_WITHDREW = "Candidate Withdrew"
    CLIENT_REJECTED = "Client Rejected"
    ROLE_ON_HOLD_CHANGED = "Role On Hold/Changed"