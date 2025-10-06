import random
import random
import secrets
import string
from datetime import timedelta, date, datetime
from typing import Tuple, Optional
from uuid import UUID

import jwt
from config.settings import SECRET_KEY
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q, Count, F, Value, Avg, IntegerField, Exists, OuterRef, Sum, When, Case
from django.db.models.functions import Concat, Cast, Round
from django.db.models.signals import pre_save
from django.utils import timezone
from django_softdelete.managers import SoftDeleteManager
from helpers.utils import delete_s3_item
from ninja_jwt.tokens import RefreshToken
from timezone_field import TimeZoneField

from accounts.enums import UserType, AuthType, GenderType, BusinessUserRoleType, NoticePeriodType, Months, Days, \
    BusinessSize, BusinessUserStatusType, CaseReasonType
from core.models import BaseModel
from jobs.enums import PhaseType, WithdrawalFeedbackType, JobStatusType, WorkStructureEnum
from notification.enums import NotificationGroup


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

    gender = models.CharField(max_length=100, choices=GenderType.choices(), default=GenderType.OTHERS.value, blank=True)
    phone_number = models.CharField(max_length=50, null=True)
    phone_code = models.CharField(max_length=50, null=True)
    email = models.EmailField(unique=True, null=True)
    email_verified = models.BooleanField(default=False)
    type = models.CharField(max_length=50, null=True, choices=UserType.choices())
    username = models.CharField(max_length=50, null=True)
    auth_mode = models.CharField(max_length=50, choices=AuthType.choices(),
                                 default=AuthType.EMAIL.value)
    facebook_id = models.CharField(max_length=50, null=True, unique=True)
    linkedin_id = models.CharField(max_length=50, null=True)
    google_id = models.CharField(max_length=50, null=True)
    apple_id = models.CharField(max_length=50, null=True)
    fullname = models.GeneratedField(
        expression=Concat(F("first_name"), Value(" "),
                          F("last_name")),
        output_field=models.CharField(),
        db_persist=True,
    )
    USERNAME_FIELD = "email"

    def __str__(self) -> str:
        return f"{self.get_full_name()}"

    def get_phone(self):
        if not self.phone_number:
            return
        if self.phone_code:
            return f"+{self.phone_code} {self.phone_number}"
        return self.phone_number

    @property
    def notification_group_name(self):
        return f"user_{self.uid}"

    def user_notification_groups(self):
        # all users and the user
        groups = {self.notification_group_name, NotificationGroup.ALL_USERS.value}
        if hasattr(self, "talents"):
            # all talents
            groups.add(NotificationGroup.TALENTS.value)
        elif hasattr(self, "businessuser"):
            # all business users
            groups.add(NotificationGroup.BUSINESS_USERS.value)
            business_user = self.businessuser
            # all business users of a business
            groups.add(f"{NotificationGroup.BUSINESS_USERS.value}_{business_user.business.uid}")
            # business user role of a business
            groups.add(f"{business_user.role}_{business_user.business.uid}")
        return groups

    @property
    def token(self):
        refresh = RefreshToken.for_user(self)
        return str(refresh.access_token)

    @property
    def unique_chat_id(self):
        return str(self.uid).replace("-", "")


    def photo_url(self):
        if hasattr(self, "talent"):
            return self.talent.photo_url
        elif hasattr(self, "businessuser"):
            return self.businessuser.business.get_logo()
        return None

    def user_type_uid(self):
        if self.type == UserType.TALENT.value:
            talent = Talent.objects.filter(user=self).first()
            if not talent:
                return
            return talent.uid
        elif self.type == UserType.BUSINESS.value:
            business_user = BusinessUser.objects.filter(user=self).first()
            if not business_user:
                return
            return business_user.uid
        return

    def delete_account(self):
        self.hard_delete()
        return


class Country(BaseModel):
    external_id = models.IntegerField(null=True)
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=4)
    phone_code = models.CharField(max_length=5, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


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

class Talent(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    whatsapp_number = models.CharField(max_length=50, null=True)
    viber_number = models.CharField(max_length=50, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    state = models.CharField(max_length=64, null=True)
    city = models.CharField(max_length=64, null=True)
    address = models.CharField(max_length=128, null=True)
    postal_code = models.CharField(max_length=20, null=True)
    employment_types = models.ManyToManyField('jobs.EmploymentType', blank=True)
    visible = models.BooleanField(default=True)
    preferred_communication = models.CharField(max_length=64, null=True)
    work_models = models.JSONField(default=list)
    bio = models.TextField(null=True)
    notice_period = models.IntegerField(null=True)
    instagram = models.URLField(null=True)
    linkedin = models.URLField(null=True)
    facebook = models.URLField(null=True)
    twitter_x = models.URLField(null=True)
    cv = models.FileField(upload_to="cvs", null=True)
    photo = models.ImageField(upload_to="talents", null=True)
    notice_period_type = models.CharField(max_length=50, choices=NoticePeriodType.choices(),
                                          default=NoticePeriodType.MONTH.value)
    native_language = models.ForeignKey("core.Language", on_delete=models.SET_NULL, null=True,
                                        related_name="native_language")
    skills = models.ManyToManyField("accounts.Skill")
    role = models.ForeignKey("accounts.Role", on_delete=models.SET_NULL, null=True)
    additional_skills = models.JSONField(default=list)
    additional_languages = models.ManyToManyField("core.Language", related_name="other_languages")
    business_models = models.ManyToManyField("jobs.BusinessModel")
    years_of_experience = models.FloatField(default=0)
    months_of_experience = models.FloatField(default=0)
    viewers = models.ManyToManyField("accounts.User", blank=True, related_name="talent_viewers")
    availability_timezone = TimeZoneField(default="America/Vancouver")
    flexible_availability = models.BooleanField(default=False)

    def get_address(self):
        data = list()
        # if self.address:
        #     data.append(self.address)

        if self.city:
            data.append(self.city)
        if self.state:
            data.append(self.state)
        if self.country:
            data.append(self.country.name)
        if self.postal_code:
            data.append(self.postal_code)
        return ", ".join(data)

    @property
    def photo_url(self):
        return self.photo.url if self.photo else None

    @property
    def cv_url(self):
        return self.cv.url if self.cv else None

    def get_years_of_experience(self):
        return f"{self.months_of_experience // 12} years {self.months_of_experience % 12} months"

    def get_skills(self):
        from accounts.schemas.talent import SkillSchema, TalentSkillSchema

        categories = SkillCategory.objects.only("id", "name")
        data = list()
        for category in categories:
            data.append(TalentSkillSchema(
                category=category.name,
                skills=[SkillSchema.from_orm(skill) for skill in self.skills.filter(category_id=category.id).iterator()]
            ))
        return data


    def get_available_days(self):
        from accounts.schemas.talent import TalentAvailableDaySchema

        data = list()
        for value in Days.values():
            availability = self.talentavailableday_set.filter(day=value).first()
            if availability:
                data.append({
                    "day": value,
                    "availability": TalentAvailableDaySchema.from_orm(availability) if availability else None
                })
        return data


    def experience_history(self):
        return self.experience_set.all()

    def education_history(self):
        return self.education_set.all()

    def calculate_years_of_experience(self)->Tuple[int, int]:
        """
        Calculate years and months of experience
        returns (years, months)
        """
        experiences = self.experience_set.only("start_date", "end_date")
        if not experiences:
            return 0,0
        start_date: date = experiences.order_by("start_date").first().start_date
        end_date: date = experiences.order_by("end_date").last().end_date
        if not end_date:
            end_date = timezone.now().date()
        months = (end_date - start_date).days/30
        return int(months//12), int(months)

    def job_post_matches(self, job_only=False, by_talent_country=False, start_date: date=None, end_date: date=None, business=None):
        from jobs.models import JobPost, Job
        from jobs.queries import add_job_post_annotations

        
        job_matching_query = Q()

        # Add optional date filter
        if start_date and end_date:
            job_matching_query &= Q(created_at__range=[start_date, end_date])

        # Query Job table with optimized prefetch and select_related
        if business:
            job_matching_query &= Q(created_by__business=business)
        jobs = (Job.objects.prefetch_related("requiredattribute", "additional_languages", "skills", 'jobpost', 'availableday')
                .filter(job_matching_query)
                .only("id")
                .distinct("id"))

        # Return early if only jobs are needed
        if job_only:
            return jobs

        # Get job IDs to fetch matching JobPosts
        job_ids = jobs.values_list("id", flat=True)
        jobpost_filter = {"job_id__in": job_ids}
        if by_talent_country:
            jobpost_filter["country"] = self.country

        queryset = JobPost.objects.select_related("job", "country", "job__role", "job__created_by__business") \
            .filter(**jobpost_filter) \
            .order_by("-id")
        
        queryset = add_job_post_annotations(queryset, self)
        queryset = queryset.filter(computed_match_score__gte=50, status=JobStatusType.POSTED.value)
        return queryset

    def job_match_score(self, job_post):
        jobpost = self.job_post_matches().filter(id=job_post.id).first()
        if not jobpost:
            return 0
        return jobpost.computed_match_score or 0


    def availability_query(self):
        working_hours_query = Q()

        for availability in self.talentavailableday_set.all():
            if not(availability.end_time and availability.start_time):
                continue
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
        from jobs.models import JobPost, SavedJob
        from jobs.queries import add_job_post_annotations

        is_saved = Exists(SavedJob.objects.filter(job_post__id=OuterRef("id"), talent=self))
        queryset = JobPost.objects.select_related(
            "job", "country", "job__role", "job__created_by__business"
        ).annotate(is_saved=is_saved).filter(is_saved=True)
        queryset = add_job_post_annotations(queryset, self)
        return queryset

    def applied_jobs(self):
        from jobs.models import JobPost, JobApplication
        from jobs.queries import add_job_post_annotations
        
        is_applied = Exists(JobApplication.objects.filter(job_post__id=OuterRef("id"), applicant=self))
        queryset = JobPost.objects.select_related(
            "job", "country", "job__role", "job__created_by__business"
        ).annotate(is_applied=is_applied).filter(is_applied=True)
        queryset = add_job_post_annotations(queryset, self)
        return queryset

    def invitations_to_apply(self, start_date:date=None, end_date:date=None)->int:
        from jobs.models import JobInvite
        queryset = JobInvite.objects.filter(talent=self)
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        return queryset.count()

    def job_interviews(self, start_date:date=None, end_date:date=None):
        from jobs.models import JobInterview
        query = Q(application__applicant=self)
        if start_date and end_date:
            query = Q(query, created_at__range=[start_date, end_date])
        return JobInterview.objects.select_related('application').filter(query)

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


    def dashboard_charts(self):
        return {
            "applications": self.applications_made_chart(),
            "interviews": self.interviews_chart()
        }

    def notifications(self, viewed:Optional[bool]=None):
        from notification.models import Notification
        recipients_query = Q(all_recipients__id=self.user.id)
        notifications = Notification.objects.filter(recipients_query)

        if viewed is True:
            notifications = notifications.filter(
                viewers__id=self.user.id
            )
        elif viewed is False:
            notifications = notifications.exclude(
                viewers__id=self.user.id
            )
        return notifications.order_by("-id")

    def delete_account(self):
        self.savedjob_set.all().hard_delete()
        self.education_set.all().hard_delete()
        self.experience_set.all().hard_delete()
        self.whatsapp_number = None
        self.viber_number = None
        self.country = None
        self.state = None
        self.city = None
        self.address = None
        self.postal_code = None
        self.bio = None
        self.instagram = None
        self.linkedin = None
        self.twitter_x = None
        self.notice_period = None
        self.additional_skills = list()
        self.skills.clear()
        self.business_models.clear()
        self.save()
        if self.photo:
            delete_s3_item(self.photo.url)
            self.photo.delete()
        self.photo = None
        if self.cv:
            delete_s3_item(self.cv.url)
            self.cv.delete()
        self.cv = None
        self.save()
        self.delete()


class BusinessIndustry(BaseModel):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Business(BaseModel):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=128, null=True)
    size = models.CharField(null=True, choices=BusinessSize.choices())
    description = models.TextField(null=True)
    website = models.URLField(null=True)
    address = models.CharField(max_length=128, null=True)
    country = models.ForeignKey("Country", on_delete=models.SET_NULL, null=True)
    logo = models.ImageField(upload_to="media/logo/", null=True)
    instagram = models.URLField(null=True)
    linkedin = models.URLField(null=True)
    facebook = models.URLField(null=True)
    twitter_x = models.URLField(null=True)
    industry = models.ForeignKey(BusinessIndustry, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name}"

    def location(self):
        return f"{self.address}, {self.country}"

    def get_logo(self):
        if not self.logo:
            return
        return self.logo.url

    def total_hires(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        queryset = JobApplication.objects.filter(stage__created_by__business=self,
                                                 stage__phase=PhaseType.HIRED.value)
        # filtering based on date hired not date created
        if start_date and not end_date:
            queryset = queryset.filter(stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            queryset = queryset.filter(stage_date_updated__lte=end_date)
        elif start_date and end_date:
            queryset = queryset.filter(stage_date_updated__range=[start_date, end_date])
        if role_id:
            queryset = queryset.filter(job_post__job__role_id=role_id)
        if client:
            queryset = queryset.filter(job_post__job__hiring_company_name=client)
        return queryset.count()

    def total_open_roles(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        # open roles are job posts that are posted
        queryset = self.job_posts(status=JobStatusType.POSTED.value)
        if start_date and not end_date:
            queryset = queryset.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            queryset = queryset.filter(created_at__lte=end_date)
        elif start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        if role_id:
            queryset = queryset.filter(job__role_id=role_id)
        if client:
            queryset = queryset.filter(job__hiring_company_name=client)
        return queryset.count()

    def total_applicants(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):

        queryset = Q(jobapplication__stage__created_by__business=self)

        if start_date and not end_date:
            queryset = queryset & Q(jobapplication__created_at__gte=start_date)
        elif end_date and not start_date:
            queryset = queryset & Q(jobapplication__created_at__lte=end_date)
        elif start_date and end_date:
            queryset = queryset & Q(jobapplication__created_at__range=[start_date, end_date])
        if role_id:
            queryset = queryset & Q(jobapplication__job_post__job__role_id=role_id)
        if client:
            queryset = queryset & Q(jobapplication__job_post__job__hiring_company_name=client)

        return Talent.objects.annotate(application_count=Count("jobapplication", filter=queryset)).filter(
            application_count__gt=0).count()

    def average_days_to_hire(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import TalentApplicationStageTimeline
        queryset = TalentApplicationStageTimeline.add_time_spent_annotation(TalentApplicationStageTimeline.objects.filter(stage__created_by__business=self,
                                application__stage__phase=PhaseType.HIRED.value).exclude(
            stage__phase=PhaseType.HIRED.value
        ))
        # filtering based on date hired not date created
        if start_date and not end_date:
            queryset = queryset.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            queryset = queryset.filter(created_at__lte=end_date)
        elif start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        if role_id:
            queryset = queryset.filter(job_role_id=role_id)
        if client:
            queryset = queryset.filter(application__job_post__job__hiring_company_name=client)

        return queryset.values("application").annotate(total_time=Sum("time_spent")).aggregate(
            days_to_hire=Cast(Avg("total_time"), output_field=IntegerField())
        )["days_to_hire"] or 0

    def total_invitations_sent(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobInvite

        queryset = JobInvite.objects.filter(job__created_by__business=self)
        if start_date and not end_date:
            queryset = queryset.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            queryset = queryset.filter(created_at__lte=end_date)
        elif start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        if role_id:
            queryset = queryset.filter(job__role_id=role_id)
        if client:
            queryset = queryset.filter(job__hiring_company_name=client)
        return queryset.count()

    def total_location_of_hires(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobPost
        queryset = JobPost.objects.filter(recruiter__business=self, jobapplication__stage__phase=PhaseType.HIRED.value)
        if start_date and not end_date:
            queryset = queryset.filter(jobapplication__stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            queryset = queryset.filter(jobapplication__stage_date_updated__lte=end_date)
        elif start_date and end_date:
            queryset = queryset.filter(jobapplication__stage_date_updated__range=[start_date, end_date])
        if role_id:
            queryset = queryset.filter(job__role_id=role_id)
        if client:
            queryset = queryset.filter(job__hiring_company_name=client)
        return queryset.only("country").distinct("country").count()


    def recruiter_performance(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        total_hires = self.total_hires(start_date, end_date, role_id, client)
        performance = JobApplication.objects\
                .filter(stage__phase=PhaseType.HIRED.value, recruiter__business=self)
        if start_date and not end_date:
            performance = performance.filter(stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            performance = performance.filter(stage_date_updated__lte=end_date)
        elif start_date and end_date:
            performance = performance.filter(stage_date_updated__range=[start_date, end_date])
        if role_id:
            performance = performance.filter(job_post__job__role_id=role_id)
        if client:
            performance = performance.filter(job_post__job__hiring_company_name=client)
        return (total_hires,
                performance.values("recruiter_id").annotate(
                    recruiter=F("recruiter__user__fullname"),
                    count=Count("recruiter_id"))
                .values("recruiter", "count")
                .order_by("-count"))

    def location_of_hires(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        total_location_of_hires = self.total_location_of_hires(start_date, end_date, role_id, client)
        hires_location = JobApplication.objects\
                .filter(stage__phase=PhaseType.HIRED.value, stage__created_by__business=self)
        if start_date and not end_date:
            hires_location = hires_location.filter(stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            hires_location = hires_location.filter(stage_date_updated__lte=end_date)
        elif start_date and end_date:
            hires_location = hires_location.filter(stage_date_updated__range=[start_date, end_date])
        if role_id:
            hires_location = hires_location.filter(job_post__job__role_id=role_id)
        if client:
            hires_location = hires_location.filter(job_post__job__hiring_company_name=client)

        return (total_location_of_hires,
                hires_location.values("job_post__country_id").annotate(
                    country=F("job_post__country__name"),
                    count=Count("job_post__country_id"))
                .order_by("-count")
                .values("country", "count"))


    def hired_genders(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        query = Q(jobapplication__stage__phase=PhaseType.HIRED.value, jobapplication__stage__created_by__business=self)
        if start_date and not end_date:
            query = query & Q(jobapplication__stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            query = query & Q(jobapplication__stage_date_updated__lte=end_date)
        elif start_date and end_date:
            query = query & Q(jobapplication__stage_date_updated__range=[start_date, end_date])
        if role_id:
            query = query & Q(jobapplication__job_post__job__role_id=role_id)
        if client:
            query = query & Q(jobapplication__job_post__job__hiring_company_name=client)
        talents = Talent.objects.annotate(
            application_count=Count("jobapplication",
                                    filter=query),
            gender=F("user__gender")).filter(
            application_count__gt=0
        )
        agg = [dict(
            gender=gender,
            count=talents.filter(gender=gender).count()
        ) for gender in GenderType.values()]
        agg.sort(key=lambda x: x["count"], reverse=True)
        return talents.count(), agg


    def applicants_by_gender(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        query = Q(jobapplication__stage__created_by__business=self)
        if start_date and not end_date:
            query = query & Q(jobapplication__stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            query = query & Q(jobapplication__stage_date_updated__lte=end_date)
        elif start_date and end_date:
            query = query & Q(jobapplication__stage_date_updated__range=[start_date, end_date])
        if role_id:
            query = query & Q(jobapplication__job_post__job__role_id=role_id)
        if client:
            query = query & Q(jobapplication__job_post__job__hiring_company_name=client)
        talents = Talent.objects.annotate(
            application_count=Count("jobapplication",
                                    filter=query),
            gender=F("user__gender")).filter(
            application_count__gt=0
        )
        agg = [dict(
            gender=gender,
            count=talents.filter(gender=gender).count()
        )for gender in GenderType.values()]
        agg.sort(key=lambda x: x["count"], reverse=True)
        return talents.count(), agg


    @staticmethod
    def job_role_stage_timeline(job_role_id, stages):
        graph = stages.annotate(avg_timelines=Avg("time_spent",
                  filter=Q(talentapplicationstagetimeline__job_role_id=job_role_id,
                           talentapplicationstagetimeline__application__deleted_at__isnull=True)),
                 stage=F("name"))
        graph = graph.annotate(avg_timeline=Case(
            When(Q(avg_timelines__isnull=True), then=float(0)),
            default=Round(F("avg_timelines"), 0),
        ))
        return {"graph": graph.values("stage", "avg_timeline"), "days_to_hire": int(graph.aggregate(Sum("avg_timeline"))["avg_timeline__sum"] or 0)}

    @staticmethod
    def job_role_phase_timeline(job_role_id, stages):
        graph = stages.values("phase").annotate(avg_timelines=Avg("time_spent",
                                                  filter=Q(talentapplicationstagetimeline__job_role_id=job_role_id,
                                                           talentapplicationstagetimeline__stage__phase=F("phase"),
                                                           talentapplicationstagetimeline__application__deleted_at__isnull=True)))
        graph = graph.annotate(avg_timeline=Case(
            When(Q(avg_timelines__isnull=True), then=float(0)) , default=Round(F("avg_timelines"), 0)
        ))
        actual_graph = list()
        days_to_hire = 0
        graph_dict = {dt["phase"]: dt["avg_timeline"] for dt in graph.values("phase", "avg_timeline")}
        for phase in PhaseType.values():
            if phase in (PhaseType.REJECTED.value, PhaseType.HIRED.value):
                continue
            actual_graph.append({"phase": phase, "avg_timeline": graph_dict.get(phase, 0)})
            days_to_hire += graph_dict.get(phase, 0)
        return {"graph": actual_graph,
                "days_to_hire": days_to_hire}

    def time_to_hire_via_stage(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import TalentApplicationStageTimeline
        from settings.models import WorkFlowStage
        stages = TalentApplicationStageTimeline.add_time_spent_annotation_for_stages(
            WorkFlowStage.objects.filter(created_by__business=self)
            .order_by("phase_order", "order")
            .exclude(phase__in=(PhaseType.REJECTED.value, PhaseType.HIRED.value))
        )
        timelines = TalentApplicationStageTimeline.add_time_spent_annotation(TalentApplicationStageTimeline.objects.prefetch_related("application").filter(
                stage__created_by__business=self,
                application__stage__phase=PhaseType.HIRED.value,
            ))
        if start_date and not end_date:
            timelines = timelines.filter(application__stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            timelines = timelines.filter(application__stage_date_updated__lte=end_date)
        elif start_date and end_date:
            timelines = timelines.filter(application__stage_date_updated__range=[start_date, end_date])
        if role_id:
            timelines = timelines.filter(application__job_post__job__role_id=role_id)
        if client:
            timelines = timelines.filter(application__job_post__job__hiring_company_name=client)
        timelines = (
            timelines
            .values("job_role")
            .annotate(
                role_id=F("job_role__id"),
                role_name=F("job_role__name"),
                avg_time_spent=Cast(Avg("time_spent"), output_field=IntegerField())
            )
            .order_by("-avg_time_spent")
            .distinct()[:5]
        )
        return [
            {
                "role": role["role_name"],
                **self.job_role_stage_timeline(role["role_id"], stages),
            }
            for role in timelines
        ]

    def time_to_hire(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import TalentApplicationStageTimeline
        from settings.models import WorkFlowStage
        stages = TalentApplicationStageTimeline.add_time_spent_annotation_for_stages(
            WorkFlowStage.objects.filter(created_by__business=self)
            .order_by("phase_order", "order")
            .exclude(phase__in=(PhaseType.REJECTED.value, PhaseType.HIRED.value))
        )
        timelines = TalentApplicationStageTimeline.add_time_spent_annotation(TalentApplicationStageTimeline.objects.prefetch_related("application").filter(
                stage__created_by__business=self,
                application__stage__phase=PhaseType.HIRED.value,
            ))
        if start_date and not end_date:
            timelines = timelines.filter(application__stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            timelines = timelines.filter(application__stage_date_updated__lte=end_date)
        elif start_date and end_date:
            timelines = timelines.filter(application__stage_date_updated__range=[start_date, end_date])
        if role_id:
            timelines = timelines.filter(application__job_post__job__role_id=role_id)
        if client:
            timelines = timelines.filter(application__job_post__job__hiring_company_name=client)
        timelines = (
            timelines
            .values("job_role")
            .annotate(
                role_id=F("job_role__id"),
                role_name=F("job_role__name"),
                avg_time_spent=Cast(Avg("time_spent"), output_field=IntegerField())
            )
            .order_by("-avg_time_spent")
            .distinct()[:5]
        )
        return [
            {
                "role": role["role_name"],
                **self.job_role_phase_timeline(role["role_id"], stages),
            }
            for role in timelines
        ]


    def withdrawal_reasons(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplicationWithdrawal

        data_list = JobApplicationWithdrawal.objects.prefetch_related("job_post")\
        .filter(
            job_post__recruiter__business=self
        )
        if start_date and not end_date:
            data_list = data_list.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            data_list = data_list.filter(created_at__lte=end_date)
        elif start_date and end_date:
            data_list = data_list.filter(created_at__range=[start_date, end_date])
        if role_id:
            data_list = data_list.filter(job_post__job__role_id=role_id)
        if client:
            data_list = data_list.filter(job_post__job__hiring_company_name=client)
        result_data_list = []
        for reason in WithdrawalFeedbackType:
            feed_back_type = JobApplicationWithdrawal.feedback_type_to_number(reason)
            result_data_list.append({
                "reason": reason.value,
                "count": data_list.filter(
                    feedback_type=feed_back_type
                ).count()
            })
        return data_list.count(), sorted(result_data_list, key=lambda x:x["count"], reverse=True)


    def hires_last_3_months(self, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        date_time = timezone.now() - timedelta(days=90)
        queryset = JobApplication.objects\
        .prefetch_related("recruiter", "applicant__user", "job_post__job__role")\
                .filter(
            recruiter__business=self,
            stage__phase=PhaseType.HIRED.value,
            stage_date_updated__gte=date_time
        )

        if role_id:
            queryset = queryset.filter(job_post__job__role_id=role_id)
        if client:
            queryset = queryset.filter(job_post__job__hiring_company_name=client)

        return  queryset.annotate(
            role=F("job_post__job__role__name"),
            talent=F("applicant__user__fullname"),
            hired_by=F("recruiter__user__fullname")
        ).order_by("-stage_date_updated").values("role", "talent", "hired_by")

    def applicants_years_of_experience(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        ranges = (0, (1,2), (2,3), (3,4), (5,6), (7,8), (8, 10), (10, 12), (12, 15), (15, 20), 20)
        data_list = list()
        query = Q(jobapplication__stage__created_by__business=self)
        if start_date and not end_date:
            query = query & Q(jobapplication__stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            query = query & Q(jobapplication__stage_date_updated__lte=end_date)
        elif start_date and end_date:
            query = query & Q(jobapplication__stage_date_updated__range=[start_date, end_date])
        if role_id:
            query = query & Q(jobapplication__job_post__job__role_id=role_id)
        if client:
            query = query & Q(jobapplication__job_post__job__hiring_company_name=client)
        applicants = Talent.objects.annotate(
            application_count=Count("jobapplication",
                                    filter=query),
            gender=F("user__gender")).filter(
            application_count__gt=0
        )
        for range_value in ranges:
            data = dict()
            data["years_of_experience"] = str(range_value if range_value == 0 else f"{range_value}+") if isinstance(range_value, int) else " - ".join(map(lambda x: str(x), range_value))
            if range_value == 0:
                data["count"] = applicants.filter(years_of_experience__lt=1).count()
            elif isinstance(range_value, tuple):
                data["count"] = applicants.filter(years_of_experience__gte=range_value[0],
                                                  years_of_experience__lt=range_value[1]).count()
            else:
                data["count"] = applicants.filter(years_of_experience__gte=range_value).count()
            data_list.append(data)
        return data_list

    def talent_at_each_phase(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from settings.models import WorkFlowStage

        query = Q(jobapplication__stage__phase=F('phase'), jobapplication__deleted_at__isnull=True)
        if start_date and not end_date:
            query = query & Q(jobapplication__created_at__gte=start_date)

        elif end_date and not start_date:
            query = query & Q(jobapplication__created_at__lte=end_date)

        elif start_date and end_date:
            query = query & Q(jobapplication__created_at__range=[start_date, end_date])
        if role_id:
            query = query & Q(jobapplication__job_post__job__role_id=role_id)

        if client:
            query = query & Q(jobapplication__job_post__job__hiring_company_name=client)

        return (WorkFlowStage.objects
                .prefetch_related("jobapplication", "jobapplication__job_post", "jobapplication__job_post__job", "jobapplication__jobpost__job__role")
                .filter(created_by__business=self).order_by("phase_order")
                .values("phase").annotate(
            count=Count("jobapplication", filter=query)
        ).values("phase", "count"))

    def talent_at_each_stage(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from settings.models import WorkFlowStage
        query = Q(jobapplication__stage_id=F('id'), jobapplication__deleted_at__isnull=True)
        if start_date and not end_date:
            query = query & Q(jobapplication__created_at__gte=start_date)

        elif end_date and not start_date:
            query = query & Q(jobapplication__created_at__lte=end_date)

        elif start_date and end_date:
            query = query & Q(jobapplication__created_at__range=[start_date, end_date])
        if role_id:
            query = query & Q(jobapplication__job_post__job__role_id=role_id)

        if client:
            query = query & Q(jobapplication__job_post__job__hiring_company_name=client)

        return (WorkFlowStage.objects
        .prefetch_related("jobapplication", "jobapplication__job_post", "jobapplication__job_post__job", "jobapplication__jobpost__job__role")
        .filter(created_by__business=self).order_by("phase_order", "order")
               .values("id").annotate(
            stage=F("name"),
            count=Count("jobapplication", filter=query)
        ).values("stage", "count"))


    def job_posts(self, status=None):
        from jobs.models import JobPost
        query = dict(job__created_by__business=self)
        if status:
            query["status"] = status
        return JobPost.objects.select_related("job__created_by__business").filter(**query)


class VerificationCode(BaseModel):
    def default_code():
        characters = string.digits
        return ''.join(random.choice(characters.upper()) for _ in range(6))

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
    order = models.IntegerField(default=0)


class BusinessUser(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    added_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=100, choices=BusinessUserRoleType.choices(), blank=True)
    status = models.CharField(max_length=100, choices=BusinessUserStatusType.choices(),
                              default=BusinessUserStatusType.ACTIVE.value)

    def __str__(self) -> str:
        return f"{self.user.first_name} {self.user.last_name}"

    def get_added_by(self):
        if not self.added_by:
            return None
        return str(self.added_by)

    def last_active(self):
        if self.user.last_login:
            return self.user.last_login.date()
        return None

    def notifications(self, viewed=False):
        from notification.models import Notification
        if hasattr(self, "businessusernotificationsettings"):
            return self.businessusernotificationsettings.notifications(viewed)
        return Notification.objects.none()

    def delete_account(self):
        self.user.hard_delete()
        self.hard_delete()
        return

    @property
    def talentfilter(self):
        return self.talentfilter_set.first()
    
    def get_invite_token(self):
        payload = {
            "business_user_uid": str(self.uid),
            "timestamp": str(timezone.now())
        }
        token = jwt.encode(payload, SECRET_KEY, "HS256")
        return token

    @classmethod
    def validate_invite_token(cls, token):
        try:
            data = jwt.decode(token, SECRET_KEY, "HS256")
            return data
        except jwt.DecodeError:
            return None


class Education(BaseModel):
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, default=None, null=True)
    level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True, default=None)
    start_date = models.DateField()
    end_date = models.DateField(null=True, default=None)
    major = models.CharField(max_length=64)
    university = models.CharField(max_length=64)


class Experience(BaseModel):
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, null=True)
    role = models.ForeignKey("accounts.Role", on_delete=models.SET_NULL, null=True)
    company = models.CharField(max_length=100, null=True)
    annual_salary = models.FloatField(default=0, null=True)
    annual_salary_currency = models.ForeignKey("core.Currency", on_delete=models.SET_NULL,
                                               null=True,
                                               related_name="annual_salary_currency")
    annual_salary_bonus = models.FloatField(default=0, null=True)
    annual_salary_bonus_currency = models.ForeignKey("core.Currency",
                                                     on_delete=models.SET_NULL,
                                                     null=True,
                                                     related_name="annual_salary_bonus_currency")
    level = models.ForeignKey("jobs.JobLevel", on_delete=models.SET_NULL, null=True)
    employment_type = models.ForeignKey("jobs.EmploymentType", on_delete=models.SET_NULL, null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True, default=None)
    currently_works_here = models.BooleanField()

    def duration(self):
        end_date = self.end_date if self.end_date else timezone.now().date()
        days = (end_date - self.start_date).days
        months = days // 30
        years = months // 12
        return f"{years} years, {months % 12} months"


class CustomTalentAvailableDayManager(SoftDeleteManager):
    def bulk_create(self, objs, **kwargs):
        for obj in objs:
            pre_save.send(sender=self.model, instance=obj, created=False ,raw=False, using=self.db)
        return super().bulk_create(objs, **kwargs)
    
    def bulk_update(self, objs, *args, **kwargs):
        for obj in objs:
            pre_save.send(sender=self.model, instance=obj, created=True, raw=False, using=self.db)
        return super().bulk_update(objs, *args, **kwargs)


class TalentAvailableDay(BaseModel):
    talent = models.ForeignKey("Talent", on_delete=models.CASCADE)
    day = models.CharField(max_length=50, choices=Days.choices())
    end_time = models.TimeField(null=True)
    start_time = models.TimeField(null=True)
    utc_start_time = models.TimeField(null=True)
    utc_end_time = models.TimeField(null=True)
    objects = CustomTalentAvailableDayManager()


class CustomerCase(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255, choices=CaseReasonType.choices())
    subject = models.CharField(max_length=255)
    description = models.TextField()


class TalentFilter(BaseModel):
    business_user = models.ForeignKey("accounts.BusinessUser", on_delete=models.CASCADE)
    name = models.CharField(max_length=128, default=None, null=True)
    role = models.ForeignKey("accounts.Role", on_delete=models.SET_NULL, null=True)
    industry = models.ForeignKey("accounts.Industry", on_delete=models.SET_NULL, null=True)
    location = models.CharField(max_length=128, null=True)
    languages = models.ManyToManyField("core.Language")
    educational_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True)
    maximum_notice_period = models.PositiveSmallIntegerField(null=True)
    work_structure = models.CharField(max_length=100, choices=WorkStructureEnum.choices(), null=True)
    skills = models.ManyToManyField("accounts.Skill")
