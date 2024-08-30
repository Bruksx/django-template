from typing import Any
from django.db import models
from core.models import BaseModel
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django_softdelete.managers import SoftDeleteManager
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
import random
from datetime import timedelta



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


# Create your models here.
class User(AbstractUser, BaseModel):
    objects = CustomUserManager()
    REQUIRED_FIELDS = []
    BUSINESS = "business"
    TALENT = "talent"
    TYPE_CHOICES = (
        (BUSINESS, BUSINESS),
        (TALENT, TALENT)
    )

    role = models.CharField(max_length=64, null=True)
    phone_number = models.CharField(max_length=16, null=True)
    email = models.EmailField(unique=True)
    type = models.CharField(max_length=16, null=True, choices=TYPE_CHOICES)
    username = models.CharField(max_length=32, null=True)

    USERNAME_FIELD = "email"

    def __str__(self) -> str:
        return f"{self.email}"


class Business(BaseModel):
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=128)
    size = models.IntegerField(null=True)
    description = models.TextField(null=True)
    website = models.URLField(null=True)
    location = models.CharField(max_length=128, null=True)
    logo = models.ImageField(upload_to="logo/", null=True)
    instagram = models.URLField(null=True)
    linkedin = models.URLField(null=True)
    facebook = models.URLField(null=True)
    twitter_x = models.URLField(null=True)

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
    OWNER = "owner"
    ADMIN = "admin"
    TEAM_MEMBER = "team_member"
    ROLE_CHOICES = (
        (OWNER, OWNER),
        (ADMIN, ADMIN),
        (TEAM_MEMBER, TEAM_MEMBER)
    )
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="added_business_users", null=True)
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)