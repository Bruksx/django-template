from core.enums import BaseEnum


class EntityType(BaseEnum):
    CHAT = "chat"
    JOB = "job"
    JOB_APPLICATION = "job application"
    JOB_POST = "job post"
    TALENT = "talent"
    BUSINESS = "business"
    BUSINESS_USER = "business user"
    USER = "user"
    CUSTOMER_CASE = "customer case"
    JOB_APPLICATION_WITHDRAWAL = "job application withdrawal"
    SETTINGS = "settings"

class EntityActionType(BaseEnum):
    NEW = "new"
    UPDATE = "update"
    DELETE = "delete"
    ADD = "add"

class NotificationType(BaseEnum):
    APPLICANTS = "applicants"
    MATCHING = "matching"
    SHARING = "sharing"
    PERFORMANCE = "performance"
    USER = "user"
    ASSIGNMENT = "assignment"

class NotificationGroup(BaseEnum):
    ALL_USERS = "all_users"
    TALENTS = "talents"
    BUSINESS_USERS = "business_users"
