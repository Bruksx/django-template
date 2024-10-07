import logging
import random
import secrets
import string
from datetime import timedelta, date, datetime
from typing import List

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django_softdelete.managers import SoftDeleteManager
from ninja_jwt.exceptions import AuthenticationFailed
from ninja_jwt.tokens import RefreshToken

from accounts.dtos import TokenDto
from accounts.enums import UserType, AuthType, GenderType, BusinessUserRoleType, NoticePeriodType, Months, Days
from core.models import BaseModel

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


    gender = models.CharField(max_length=32, choices=GenderType.choices(), default=GenderType.OTHERS.value)
    phone_number = models.CharField(max_length=16, null=True)
    email = models.EmailField(unique=True, null=True)
    email_verified = models.BooleanField(default=False)
    type = models.CharField(max_length=16, null=True, choices=UserType.choices())
    username = models.CharField(max_length=32, null=True)
    auth_mode = models.CharField(max_length=20, choices=AuthType.choices(),
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


    def photo_url(self):
        if hasattr(self, "talent"):
            return self.talent.photo_url
        elif hasattr(self, "businessuser"):
            return self.businessuser.business.get_logo()
        return None

class Country(BaseModel):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=4)


class SkillCategory(BaseModel):
    name = models.CharField(max_length=128)

    def __str__(self) -> str:
        return self.name

    @property
    def skills(self):
        return self.skill_set.all()

class Industry(BaseModel):
    name = models.CharField(max_length=128)

    def __str__(self) -> str:
        return self.name


class Department(BaseModel):
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)

    def __str__(self) -> str:
        return self.name


class Role(BaseModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)

    def __str__(self) -> str:
        return self.name


class Skill(BaseModel):
    name = models.CharField(max_length=128)
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.name


class AdditionalSkill(BaseModel):
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE)
    name = models.CharField(max_length=128)


class Talent(BaseModel):
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    whatsapp_number = models.CharField(max_length=16, null=True)
    viber_number = models.CharField(max_length=16, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    state = models.CharField(max_length=64, null=True)
    city = models.CharField(max_length=64, null=True)
    address = models.CharField(max_length=128, null=True)
    postal_code = models.CharField(max_length=8, null=True)
    employment_type = models.CharField(max_length=32, null=True)
    visible = models.BooleanField(default=False)
    preferred_communication = models.CharField(max_length=64, null=True)
    bio = models.TextField(null=True)
    notice_period = models.IntegerField(null=True)
    instagram = models.URLField(null=True)
    linkedin = models.URLField(null=True)
    facebook = models.URLField(null=True)
    twitter_x = models.URLField(null=True)
    cv = models.FileField(upload_to="cvs")
    photo = models.ImageField(upload_to="talents")
    notice_period_type = models.CharField(max_length=32, choices=NoticePeriodType.choices(),
                                          default=NoticePeriodType.MONTH.value)
    native_language = models.ForeignKey("core.Language", on_delete=models.SET_NULL, null=True,
                                        related_name="native_language")
    skills = models.ManyToManyField("accounts.Skill")
    additional_languages = models.ManyToManyField("core.Language", related_name="other_languages")
    business_models = models.ManyToManyField("jobs.BusinessModel")

    @property
    def photo_url(self):
        return self.photo.url if self.photo else None

    @property
    def cv_url(self):
        return self.cv.url if self.cv else None

    def get_skills(self):
        from accounts.schemas.talent import SkillSchema, TalentSkillSchema

        categories = SkillCategory.objects.only("id", "name")
        data = list()
        for category in categories:
            data.append(TalentSkillSchema(
                category=category.name,
                skills=[SkillSchema.from_orm(skill) for skill in self.skills.filter(category_id=category.id)]
            ))
        return data

    def get_additional_skills(self)->List[str]:
        return list(self.additionalskill_set.values_list("name", flat=True))


    def get_available_days(self):
        from accounts.schemas.talent import TalentAvailableDaySchema

        data = list()
        for value in Days.values():
            availability = self.talentavailableday_set.filter(day=value).first()
            data.append({
                "day": value,
                "availability": TalentAvailableDaySchema.from_orm(availability) if availability else None
            })
        return data


    def experience_history(self):
        return self.experience_set.all()

    def education_history(self):
        return self.education_set.all()

    def years_of_experience(self):
        experiences = Experience.objects.filter(talent=self).only("start_date", "end_date")
        if not experiences:
            return 0
        start_date: date = experiences.order_by("start_date").first().start_date
        end_date: date = experiences.order_by("end_date").last().end_date
        return (end_date - start_date).days//365

    def job_post_matches(self, job_only=False, start_date: date=None, end_date: date=None):
        from jobs.models import AvailableDay, JobPost

        from jobs.models import Job
        experiences = self.experience_set.only("level_id", "employment_type_id", "role_id")
        job_level_ids = experiences.values_list("level_id", flat=True)
        years_of_experience = self.years_of_experience()
        education_level_ids = self.education_set.only("level_id").values_list("level_id", flat=True)
        business_model_ids = self.business_models.only("id").values_list("id", flat=True)
        role_ids=experiences.values_list("role_id", flat=True)
        additional_language_ids = self.additional_languages.only("id").values_list("id", flat=True)
        skill_ids = self.skills.only("id").values_list("id", flat=True)

        working_hours_query = self.availability_query()

        job_matching_query = Q(
            Q(requiredattribute__job_level=True, job_level_id__in=job_level_ids)|
            Q(requiredattribute__minimum_education_level=True, minimum_education_level_id__in=education_level_ids)|
            Q(requiredattribute__business_model__id__in=business_model_ids)|
            Q(requiredattribute__role=True, role_id__in=role_ids)|
            Q(requiredattribute__years_of_experience=True, years_of_experience=years_of_experience)|
            Q(requiredattribute__first_language=True, first_language=self.native_language)|
            Q(requiredattribute__secondary_language=True, additional_languages__id__in=additional_language_ids)|
            Q(requiredattribute__working_hours=True, availableday__in=AvailableDay.objects.filter(working_hours_query))|
            Q(requiredattribute__location=True, jobpost__country=self.country),
            Q(requiredattribute__skills__id__in=skill_ids)
        )
        if start_date and end_date:
            job_matching_query = Q(job_matching_query, created_at__range=[start_date, end_date])
        jobs = Job.objects.filter(job_matching_query).only("id").distinct("id")
        if job_only:
            return jobs
        job_ids = jobs.values_list("id", flat=True)
        return JobPost.objects.filter(job_id__in=job_ids).order_by("-id")

    def job_match_score(self, job_post):
        job = job_post.job
        if not hasattr(job, "requiredattribute"):
            return 100
        required_attribute = job.requiredattribute
        requirement_score = required_attribute.total_score()
        score = requirement_score
        if required_attribute.skills.count() > 0 and required_attribute.skills.intersection(self.skills.all()).count()  == 0:
            score -= 1
        if required_attribute.role and not self.experience_set.filter(role=job.role).exists():
            score -=1
        if  required_attribute.job_level and not self.experience_set.filter(level=job.job_level).exists():
            score -=1
        if  required_attribute.years_of_experience and job.years_of_experience < job.years_of_experience:
            score -=1
        if required_attribute.business_model.count() > 0 and business_model.intersection(self.business_models.all()).count() == 0:
            score -= 1
        if required_attribute.minimum_education_level and not self.education_set.filter(level=job.minimum_education_level).exists():
            score -= 1

        if required_attribute.first_language and self.native_language != job.first_language:
            score -= 1
        if required_attribute.secondary_language and job.additional_languages.intersection(self.additional_languages.all()).count() == 0:
            score -= 1
        if required_attribute.working_hours:
            working_hours_query = self.availability_query()
            if not job.availableday_set.filter(working_hours_query).exists():
                score -= 1
        if required_attribute.location and self.country != job_post.country:
            score -= 1
        return int((score/requirement_score) * 100)


    def availability_query(self):
        working_hours_query = Q()

        for availability in self.talentavailableday_set.all():
            day_query = Q(
                day=availability.day,
                start_time__lte=availability.end_time,
                end_time__gte=availability.start_time
            )
            working_hours_query |= day_query
        return working_hours_query


    def job_applications(self, start_date:date=None, end_date:date=None):
        if start_date and end_date:
            return self.jobapplication_set.filter(created_at__range=[start_date, end_date])
        return self.jobapplication_set

    def saved_jobs(self):
        from jobs.models import JobPost
        job_post_ids = self.savedjob_set.only("job_post_id").values_list("job_post_id", flat=True)
        return JobPost.objects.filter(id__in=job_post_ids)

    def applied_jobs(self):
        from jobs.models import JobPost
        job_post_ids = self.jobapplication_set.only("job_post_id").values_list("job_post_id", flat=True)
        return JobPost.objects.filter(id__in=job_post_ids)

    def invitations_to_apply(self, start_date:date=None, end_date:date=None)->int:
        from chats.models import Message
        query = Q(conversation__users__id=self.user.id, job_post__isnull=False)
        if start_date and end_date:
            query = Q(query, created_at__range=[start_date, end_date])
        return Message.objects.filter(query).only("job_post_id").distinct("job_post_id").count()

    def job_interviews(self, start_date:date=None, end_date:date=None):
        from jobs.models import JobInterview
        query = Q(application__applicant=self)
        if start_date and end_date:
            query = Q(query, created_at__range=[start_date, end_date])
        return JobInterview.objects.filter(query)

    def applications_made_chart(self):
        from accounts.schemas.talent import MonthlyChartSchema
        current_year = datetime.now().year
        applications = self.jobapplication_set.filter(created_at__year=current_year)
        data = list()
        month = 0
        for value in Months.values():
            month +=1
            data.append(
                MonthlyChartSchema(
                    month = value,
                    count = applications.filter(created_at__month=month).count()
                )
            )
        return data

    def interviews_chart(self):
        from accounts.schemas.talent import MonthlyChartSchema
        current_year = datetime.now().year
        interviews = self.job_interviews().filter(created_at__year=current_year)
        data = list()
        month = 0
        for value in Months.values():
            month += 1
            data.append(
                MonthlyChartSchema(
                    month=value,
                    count=interviews.filter(created_at__month=month).count()
                )
            )
        return data

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

    def get_logo(self):
        if not self.logo:
            return
        return self.logo.url

class VerificationCode(BaseModel):
    def default_code():
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters.upper()) for _ in range(4))

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


class EducationLevel(BaseModel):
    industry = models.ForeignKey("accounts.Industry", on_delete=models.SET_NULL, null=True)
    level = models.CharField(max_length=64)


class BusinessUser(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="added_business_users", null=True)
    role = models.CharField(max_length=32, choices=BusinessUserRoleType.choices())

    def __str__(self) -> str:
        return self.user.email


class Education(BaseModel):
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, default=None, null=True)
    level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True, default=None)
    start_date = models.DateField()
    end_date = models.DateField()
    major = models.CharField(max_length=64)
    university = models.CharField(max_length=64)


class Experience(BaseModel):
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, null=True)
    role = models.ForeignKey("accounts.Role", on_delete=models.SET_NULL, null=True)
    company = models.CharField(max_length=100, null=True)
    annual_salary = models.FloatField(default=0)
    annual_salary_currency = models.ForeignKey("core.Currency", on_delete=models.SET_NULL,
                                               null=True,
                                               related_name="annual_salary_currency")
    annual_salary_bonus = models.FloatField(default=0)
    annual_salary_bonus_currency = models.ForeignKey("core.Currency",
                                                     on_delete=models.SET_NULL,
                                                     null=True,
                                                     related_name="annual_salary_bonus_currency")
    level = models.ForeignKey("jobs.JobLevel", on_delete=models.SET_NULL, null=True)
    employment_type = models.ForeignKey("jobs.EmploymentType", on_delete=models.SET_NULL, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    currently_works_here = models.BooleanField()


class TalentAvailableDay(BaseModel):
    talent = models.ForeignKey("Talent", on_delete=models.CASCADE)
    day = models.CharField(max_length=32, choices=Days.choices())
    end_time = models.TimeField(null=True)
    start_time = models.TimeField(null=True)


class CustomerCase(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    description = models.TextField()

