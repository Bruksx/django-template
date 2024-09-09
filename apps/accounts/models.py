import secrets
import string
from typing import Any
from django.db import models
from core.models import BaseModel
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django_softdelete.managers import SoftDeleteManager
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
import random
from datetime import timedelta

from ninja_jwt.exceptions import AuthenticationFailed
from ninja_jwt.tokens import RefreshToken

from apps.accounts.dtos import TokenDto
from apps.accounts.enums import UserType, AuthType, GenderType, BusinessUserRoleType



class CustomUserManager(SoftDeleteManager, BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

    @staticmethod
    def make_random_password(length=10, digits=True, letters=True)->str:
        alphabet = string.ascii_letters + string.digits
        if digits and not letters:
           alphabet = string.digits
        elif not digits and letters:
            alphabet = string.ascii_letters
        while True:
            password = ''.join(secrets.choice(alphabet) for i in range(length))
            if (any(c.islower() for c in password)
                    and any(c.isupper() for c in password)
                    and sum(c.isdigit() for c in password) >= 3):
                break
        return password


# Create your models here.
class User(AbstractUser, BaseModel):
    objects = CustomUserManager()
    REQUIRED_FIELDS = []


    role = models.CharField(max_length=64, null=True)
    gender = models.CharField(max_length=16, choices=GenderType.choices())
    phone_number = models.CharField(max_length=16, null=True)
    email = models.EmailField(unique=True, null=True)
    email_verified = models.BooleanField(default=False)
    type = models.CharField(max_length=16, null=True, choices=UserType.choices())
    username = models.CharField(max_length=32, null=True)
    auth_mode = models.CharField(max_length=20, choices=AuthType.choices,
                                 default=AuthType.EMAIL.value)
    facebook_id = models.CharField(max_length=32, null=True, unique=True)
    linkedin_id = models.CharField(max_length=32, null=True)
    google_id = models.CharField(max_length=32, null=True)


    USERNAME_FIELD = "email"

    def __str__(self) -> str:
        return f"{self.email}"
    
    @property
    def token(self):
        refresh = RefreshToken.for_user(self)
        return str(refresh.access_token)

    def tokens(self)->TokenDto:
        if not self.is_active:
            raise AuthenticationFailed("This user is blocked")
        refresh_token = RefreshToken.for_user(self)
        return TokenDto(access_token=str(refresh_token.access_token), refresh_token=str(refresh_token))

class Country(BaseModel):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=4)



class Talent(BaseModel):
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    state = models.CharField(max_length=64, null=True)
    city = models.CharField(max_length=64, null=True)
    postal_code = models.CharField(max_length=8, null=True)
    employment_type = models.CharField(max_length=32, null=True)
    visible = models.BooleanField(default=False)
    preferred_communication = models.CharField(max_length=64, null=True)
    bio = models.TextField(null=True)
    gender = models.CharField(max_length=16, null=True)
    notice_period = models.IntegerField(null=True)
    languages = models.ManyToManyField("Language", through="UserLanguage")
    instagram = models.URLField(null=True)
    linkedin = models.URLField(null=True)
    facebook = models.URLField(null=True)
    twitter_x = models.URLField(null=True)
    cv = models.FileField(upload_to="cvs")
    photo = models.ImageField(upload_to="talents")
    


class Business(BaseModel):
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=128)
    size = models.IntegerField(null=True)
    description = models.TextField(null=True)
    website = models.URLField(null=True)
    location = models.CharField(max_length=128, null=True)
    logo = models.ImageField(upload_to="media/logo/", null=True)
    instagram = models.URLField(null=True)
    linkedin = models.URLField(null=True)
    facebook = models.URLField(null=True)
    twitter_x = models.URLField(null=True)
    industry = models.CharField(max_length=64, null=True)

    def __str__(self):
        return self.name


class VerificationCode(BaseModel):
    def default_code():
        code = ""
        for _ in range(4):
            code += str(random.randint(0, 9))
        return code
    
    def default_expiration():
        return timezone.now() + timedelta(minutes=5)

    email = models.EmailField()
    code = models.CharField(max_length=128, default=default_code)
    expires_at = models.DateTimeField(default=default_expiration)
    length = models.IntegerField(default=4)

    def save(self, *args, **kwargs):
        unhashed_code = self.code
        if not self.pk: 
            self.code = make_password(self.code)
        super().save(*args, **kwargs)
        return unhashed_code

    def verify_code(self, code_to_check):
        return check_password(code_to_check, self.code)

    def __str__(self):
        return f"VerificationCode(email={self.email})"
    
    def has_expired(self):
        return timezone.now() > self.expires_at


class BusinessUser(BaseModel):

    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="added_business_users", null=True)
    role = models.CharField(max_length=32, choices=BusinessUserRoleType.choices())


class Education(BaseModel):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    level = models.CharField()
    start_date = models.DateField()
    end_date = models.DateField()
    major = models.CharField(max_length=64)
    university = models.CharField(max_length=64)


class Experience(BaseModel):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    role = models.CharField(max_length=32)
    role_type = models.ForeignKey("jobs.EmploymentType", on_delete=models.SET_NULL, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    currently_works_here = models.BooleanField()


class Language(BaseModel):
    name = models.CharField(max_length=32)

    def __str__(self) -> str:
        return self.name


class UserLanguage(BaseModel):
    talent = models.ForeignKey(Talent, on_delete=models.DO_NOTHING, null=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    is_native = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.language}({self.user})"

class TalentAvailability(BaseModel):
    talent = models.OneToOneField(Talent, on_delete=models.CASCADE)
    monday = models.BooleanField(default=False)
    monday_start_time = models.TimeField(default=None, null=True)
    monday_end_time = models.TimeField(default=None, null=True)
    tuesday = models.BooleanField(default=False)
    tuesday_start_time = models.TimeField(default=None, null=True)
    tuesday_end_time = models.TimeField(default=None, null=True)
    wednesday = models.BooleanField(default=False)
    wednesday_start_time = models.TimeField(default=None, null=True)
    wednesday_end_time = models.TimeField(default=None, null=True)
    thursday = models.BooleanField(default=False)
    thursday_start_time = models.TimeField(default=None, null=True)
    thursday_end_time = models.TimeField(default=None, null=True)
    friday = models.BooleanField(default=False)
    friday_start_time = models.TimeField(default=None, null=True)
    friday_end_time = models.TimeField(default=None, null=True)
    saturday = models.BooleanField(default=False)
    saturday_start_time = models.TimeField(default=None, null=True)
    saturday_end_time = models.TimeField(default=None, null=True)
    sunday = models.BooleanField(default=False)
    sunday_start_time = models.TimeField(default=None, null=True)
    sunday_end_time = models.TimeField(default=None, null=True)
