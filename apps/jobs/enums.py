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
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    TEXT = "text"
    FILE = "file"


class RequiredAttributeType(BaseEnum):
    WORK_STRUCTURE = "work_structure"
    FIRST_LANGUAGE = "first_language"
    LOCATION = "location"
    TECHNOLOGICAL_REQUIREMENTS = "technological_requirements"
    WORKING_HOURS = "working_hours"