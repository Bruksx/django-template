from typing import List, Optional, Union

from ninja import Field
from ninja import Schema
from pydantic_core.core_schema import AnySchema


class Option(Schema):
    label: str
    value: str


class Condition(Schema):
    id: str
    value: str


class QualificationMatch(Schema):
    type: str
    values: List[str]


class Qualification(Schema):
    type: str
    match: QualificationMatch


class QuestionBase(Schema):
    id: str
    question: str
    required: Optional[bool] = False
    condition: Optional[Condition] = None


class TextQuestion(QuestionBase):
    type: str = Field("text")
    format: Optional[str] = None
    min: Optional[int] = None
    max: Optional[int] = None


class TextareaQuestion(QuestionBase):
    type: str = Field("textarea")


class SelectQuestion(QuestionBase):
    type: str = Field("select")
    options: List[Option]


class MultiselectQuestion(QuestionBase):
    type: str = Field("multiselect")
    options: List[Option]
    qualification: Optional[Qualification] = None


class HierarchicalOption(Schema):
    id: str
    options: List[Option]
    condition: Condition


class HierarchicalQuestion(QuestionBase):
    type: str = Field("hierarchical")
    options: List[Option]
    hierarchicalOptions: List[HierarchicalOption]


class DateQuestion(QuestionBase):
    type: str = Field("date")
    format: Optional[str] = None


class FileQuestion(QuestionBase):
    type: str = Field("file")


class PagebreakQuestion(QuestionBase):
    type: str = Field("pagebreak")


class InformationQuestion(QuestionBase):
    type: str = Field("information")
    text: str


ScreenerQuestion = Union[
    TextQuestion,
    TextareaQuestion,
    SelectQuestion,
    MultiselectQuestion,
    HierarchicalQuestion,
    DateQuestion,
    FileQuestion,
    PagebreakQuestion,
    InformationQuestion,
]


class ScreenerQuestions(Schema):
    questions: List[ScreenerQuestion]


class DemographicQuestion(QuestionBase):
    type: str = Field("select")
    options: List[Option]


class DemographicQuestions(Schema):
    questions: List[DemographicQuestion]


class WidgetScreenerSchema(Schema):
    schemaVersion: str = Field("1.0")
    screenerQuestions: ScreenerQuestions
    demographicQuestions: Optional[DemographicQuestions] = None

class JobSchema(Schema):
    jobId: str  # ID of the job for internal tracking
    jobKey: str  # Unique ID for the aggregated job on Indeed (max 16 ASCII characters)
    jobUrl: str  # URL of the job listing (could be Indeed or the client's career site)
    jobMeta: Optional[str] = None  # Additional metadata for the job (not visible externally)
    jobTitle: str  # Title of the job
    jobCompany: str  # Name of the company
    jobLocation: str  # Location of the job

class ResumeSchema(Schema):
    file: Optional[str] = None  # Binary file (e.g., URL to the file or base64 encoded content)
    text: Optional[str] = None  # Text representation of the resume (if using Indeed Resume)
    html: Optional[str] = None  # HTML representation of the resume (if using Indeed Resume)
    json: Optional[dict] = None  # JSON

class ApplicantSchema(Schema):
    fullName: str  # Full name (e.g., "John Doe")
    firstName: Optional[str] = None  # First name (Optional if fullName is provided)
    lastName: Optional[str] = None  # Last name (Optional if fullName is provided)
    email: str  # Email address
    phoneNumber: Optional[str] = None  # Phone number (Optional)
    coverletter: Optional[str] = None  # Cover letter (Optional)
    resume: Optional[ResumeSchema] = None  # Resume (Optional, could be more detailed)
    verified: bool  # Whether the applicant's email is verified (True or False)


class QuestionAnswerSchema(Schema):
    question: ScreenerQuestion
    answer: Union[str, list, dict]


class ScreenerQuestionsAndAnswersSchema(Schema):
    url: str  # URL from which the questions were retrieved
    retrievedOnMillis: int  # The time when the questions were retrieved (UNIX time in milliseconds)
    questionsAndAnswers: List[QuestionAnswerSchema]  # List of question-answer pairs
    schemaVersion: str  # The version of the questions and answers schema


class SourceAttributionSchema(Schema):
    enumKey: str  # The key identifying the source (e.g., "AUTOSOURCER")
    name: str  # The name of the source (e.g., "Indeed Autosourcer")


class AnalyticsSchema(Schema):
    ip: str  # IP address of the applicant
    referer: Optional[str] = None  # Page that contains the Apply button, if present
    targetedApplyAd: bool  # True if it's an Indeed Apply ad served on Indeed
    trackingUid: str  # Unique tracking ID used internally by Indeed
    sponsored: bool  # True if the job is sponsored
    advNum: str  # Indeed Advertiser number ID attached to the claimed job and application
    userAgent: str  # Software agent details used by the applicant (browser info)
    device: str  # Device used by the applicant (desktop, mobile, etc.)
    completeApplicationSourceAttribution: List[SourceAttributionSchema]  # L

class IndeedApplicationData(Schema):
    id: str  # Unique ID for the application (apply_id)
    appliedOnMillis: int  # Date and time when the applicant applied in UNIX timestamp (milliseconds)

    job: JobSchema
    applicant: ApplicantSchema
    analytics: AnalyticsSchema

    locale: str  # Locale from which the applicant applied

    screenerQuestionsAndAnswers: List[ScreenerQuestionsAndAnswersSchema] = []
    demographicQuestionsAndAnswers: List[ScreenerQuestionsAndAnswersSchema] = []

    schemaVersion: str  # Version of the questions and answers schema deli
