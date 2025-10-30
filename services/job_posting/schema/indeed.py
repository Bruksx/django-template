from typing import List, Optional, Union

from ninja import Field
from ninja import Schema


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


