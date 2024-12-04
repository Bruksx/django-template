from accounts.models import Department, Role,  Country, User, BusinessUser
from core.models import BaseManager
from django.shortcuts import get_object_or_404


class JobManager(BaseManager):
    ...