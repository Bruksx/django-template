from apps.core.enums import BaseEnum


class UserType(BaseEnum):
    BUSINESS = "business"
    TALENT = "talent"

class GenderType(BaseEnum):
    MALE = "male"
    FEMALE = "female"
    OTHERS = "others"

class SocialType(BaseEnum):
    GOOGLE = "Google"
    LINKEDIN = "LinkedIn"
    FACEBOOK = "Facebook"

class AuthType(BaseEnum):
    GOOGLE = "Google"
    LINKEDIN = "LinkedIn"
    FACEBOOK = "Facebook"
    EMAIL = "email"

class BusinessUserRoleType(BaseEnum):
    OWNER = "owner"
    ADMIN = "admin"
    TEAM_MEMBER = "team_member"