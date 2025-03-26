from core.enums import BaseEnum


class UserType(BaseEnum):
    BUSINESS = "business"
    TALENT = "talent"

class SocialType(BaseEnum):
    GOOGLE = "google"
    LINKEDIN = "linkedIn"
    FACEBOOK = "facebook"
    APPLE = "apple"

class AuthType(BaseEnum):
    GOOGLE = "Google"
    LINKEDIN = "LinkedIn"
    FACEBOOK = "Facebook"
    APPLE = "Apple"
    EMAIL = "Email"

class BusinessUserRoleType(BaseEnum):
    OWNER = "owner"
    ADMIN = "admin"
    TEAM_MEMBER = "team_member"

class BusinessUserStatusType(BaseEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    DELETED = "deleted"

class NoticePeriodType(BaseEnum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTH = "months"

class GenderType(BaseEnum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non-binary"
    OTHERS = "prefer to self describe"

class PreferredCommunicationType(BaseEnum):
    TEXT = "text"
    WHATSAPP = "whatsapp"
    VIBER = "viber"
    EMAIL = "email"

class Months(BaseEnum):
    JANUARY = "Jan"
    FEBRUARY = "Feb"
    MARCH = "Mar"
    APRIL = "Apr"
    MAY = "May"
    JUNE = "Jun"
    JULY = "Jul"
    AUGUST = "Aug"
    SEPTEMBER = "Sept"
    OCTOBER = "Oct"
    NOVEMBER = "Nov"
    DECEMBER = "Dec"

class Days(BaseEnum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"

class MeetingType(BaseEnum):
    GOOGLE_MEET = "google_meet"
    ZOOM = "zoom"
    MICROSOFT_TEAMS = "microsoft_teams"

class BusinessSize(BaseEnum):
    SIZE_0_10 = "0-10 Employees"
    SIZE_11_50 = "11-50 Employees"
    SIZE_51_250 = "51-250 Employees"
    SIZE_251_1000 = "251-1000 Employees"
    SIZE_1001_5000 = "1001-5000 Employees"
    SIZE_5001_10000 = "5001-10,000 Employees"
    SIZE_10000_PLUS = "10,001+ Employees"

class CaseReasonType(BaseEnum):
    TECHNICAL_ISSUES = "Technical Issues"
    SYSTEM_HELP = "System Help"
    REPORT_BUSINESS = "Report a Business"
    OTHERS = "Others"