from apps.core.enums import BaseEnum


class UserType(BaseEnum):
    BUSINESS = "business"
    TALENT = "talent"

class SocialType(BaseEnum):
    GOOGLE = "google"
    LINKEDIN = "linkedIn"
    FACEBOOK = "facebook"

class AuthType(BaseEnum):
    GOOGLE = "Google"
    LINKEDIN = "LinkedIn"
    FACEBOOK = "Facebook"
    EMAIL = "email"

class BusinessUserRoleType(BaseEnum):
    OWNER = "owner"
    ADMIN = "admin"
    TEAM_MEMBER = "team_member"

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