from ninja.errors import HttpError

from apps.accounts.enums import BusinessUserRoleType


class Permission:
    __message__ = "not allowed"


    @classmethod
    def __has_permission__(cls, request, *args, **kwargs):
        return True

    @classmethod
    def __validate__(cls, request, *args, **kwargs):
        if not cls.__has_permission__(request, *args, **kwargs):
            raise HttpError(403, cls.__message__)
        return

    @classmethod
    def check(cls, request, raise_exception=True, *args, **kwargs):
        try:
            cls.__validate__(request, *args, **kwargs)
            return True
        except HttpError as e:
            if raise_exception is True:
                raise e
            return False


class IsAuthenticated(Permission):

    __message__ = "You are not logged in"

    @classmethod
    def __has_permission__(cls, request, *args, **kwargs):
        return request.user.is_authenticated

    @classmethod
    def __validate__(cls, request, *args, **kwargs):
        if not super().__has_permission__(request):
            raise HttpError(403, super().__message__)
        if not cls.__has_permission__(request):
            raise HttpError(403, cls.__message__)
        return




class IsBusinessUser(IsAuthenticated):
    __message__ = "You are not a business staff"

    @classmethod
    def __has_permission__(
        cls, request, *args, **kwargs
    ) -> bool:
        return hasattr(request.user, "businessuser")

    @classmethod
    def __validate__(cls, request, *args, **kwargs):
        # check preceding permissions
        if not super().__has_permission__(request):
            raise HttpError(403, super().__message__)
        # check current permission
        if not cls.__has_permission__(request):
            raise HttpError(403, cls.__message__)
        return

class IsTalentUser(IsAuthenticated):
    __message__ = "You are not a talent"

    @classmethod
    def __has_permission__(
        cls, request, *args, **kwargs) -> bool:
        return hasattr(request.user, "talent")

    @classmethod
    def __validate__(cls, request, *args, **kwargs):
        if not super().__has_permission__(request):
            raise HttpError(403, super().__message__)
        if not cls.__has_permission__(request):
            raise HttpError(403, cls.__message__)
        return


class IsAdminStaff(IsBusinessUser):
    __message__ = "You are not an admin staff"

    @classmethod
    def __has_permission__(
        cls, request, *args, **kwargs) -> bool:
        return request.user.businessuser.role == BusinessUserRoleType.ADMIN.value

    @classmethod
    def __validate__(cls, request, *args, **kwargs):
        if not super().__has_permission__(request):
            raise HttpError(403, super().__message__)
        if not cls.__has_permission__(request):
            raise HttpError(403, cls.__message__)
        return


class IsBusinessOwner(IsBusinessUser):
    __message__ = "You are not a business owner"

    @classmethod
    def __has_permission__(
            cls, request, *args, **kwargs) -> bool:
        return request.user.businessuser.role == BusinessUserRoleType.OWNER.value

    @classmethod
    def __validate__(cls, request, *args, **kwargs):
        if not super().__has_permission__(request):
            raise HttpError(403, super().__message__)
        if not cls.__has_permission__(request):
            raise HttpError(403, cls.__message__)
        return


class IsBusinessTeamMember(IsBusinessUser):
    __message__ = "You are not a business team member"

    @classmethod
    def __has_permission__(
            cls, request, *args, **kwargs) -> bool:
        return request.user.businessuser.role == BusinessUserRoleType.TEAM_MEMBER.value

    @classmethod
    def __validate__(cls, request, *args, **kwargs):
        if not super().__has_permission__(request):
            raise HttpError(403, super().__message__)
        if not cls.__has_permission__(request):
            raise HttpError(403, cls.__message__)
        return


class IsBusinessOwnerOrAdmin(IsBusinessUser):
    __message__ = "You are not a business owner or admin"

    @classmethod
    def __has_permission__(cls, request, *args, **kwargs) -> bool:
        return request.user.businessuser.role in [BusinessUserRoleType.OWNER.value, BusinessUserRoleType.ADMIN.value]

    @classmethod
    def __validate__(cls, request, *args, **kwargs):
        if not super().__has_permission__(request):
            raise HttpError(403, super().__message__)
        if not cls.__has_permission__(request):
            raise HttpError(403, cls.__message__)
        return

