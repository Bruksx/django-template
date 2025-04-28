import random
import secrets
import string
from datetime import timedelta, date, datetime
from typing import Tuple, Optional
from uuid import UUID

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q, Count, F, Value, Avg, IntegerField
from django.db.models.functions import Concat, Cast
from django.utils import timezone
from django_softdelete.managers import SoftDeleteManager
from helpers.utils import delete_s3_item
from ninja_jwt.tokens import RefreshToken

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

    gender = models.CharField(max_length=100, choices=GenderType.choices(), default=GenderType.OTHERS.value)
    phone_number = models.CharField(max_length=50, null=True)
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

    def delete_account(self):
        if hasattr(self, "talent"):
            self.talent.delete_account()
        elif hasattr(self, "businessuser"):
            self.businessuser.delete_account()
        self.first_name = "deleted"
        self.last_name = "user"
        self.email = f"deleted_user_{self.id}@example.com"
        self.phone_number = None
        self.facebook_id = None
        self.linkedin_id = None
        self.google_id = None
        self.apple_id = None
        self.username = f"user-{self.id}"
        self.is_active = False
        self.save()
        self.delete()
        return


class Country(BaseModel):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=4)

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
    employment_type = models.ForeignKey("jobs.EmploymentType", on_delete=models.SET_NULL, null=True)
    visible = models.BooleanField(default=True)
    preferred_communication = models.CharField(max_length=64, null=True)
    work_model = models.CharField(max_length=64, null=True, choices=WorkStructureEnum.choices())
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
    additional_skills = models.JSONField(default=list)
    additional_languages = models.ManyToManyField("core.Language", related_name="other_languages")
    business_models = models.ManyToManyField("jobs.BusinessModel")
    years_of_experience = models.FloatField(default=0)
    months_of_experience = models.FloatField(default=0)
    viewers = models.ManyToManyField("accounts.User", blank=True, related_name="talent_viewers")

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
                skills=[SkillSchema.from_orm(skill) for skill in self.skills.filter(category_id=category.id)]
            ))
        return data


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

    def job_post_matches(self, job_only=False, by_talent_country=False, start_date: date=None, end_date: date=None):
        from jobs.models import AvailableDay, JobPost

        from jobs.models import Job
        experiences = self.experience_set.only("level_id", "employment_type_id", "role_id")
        job_level_ids = experiences.values_list("level_id", flat=True)
        years_of_experience = int(self.years_of_experience)
        education_level_ids = self.education_set.only("level_id").values_list("level_id", flat=True)
        business_model_ids = self.business_models.only("id").values_list("id", flat=True)
        role_ids=experiences.values_list("role_id", flat=True)
        additional_language_ids = self.additional_languages.only("id").values_list("id", flat=True)
        skill_ids = self.skills.only("id").values_list("id", flat=True)

        working_hours_query = self.availability_query()

        job_matching_query = Q(
            Q(requiredattribute__job_level=True, job_level_id__in=job_level_ids)|
            Q(requiredattribute__minimum_education_level=True, minimum_education_level_id__in=education_level_ids)|
            Q(requiredattribute__business_models__id__in=business_model_ids)|
            Q(requiredattribute__role=True, role_id__in=role_ids)|
            Q(requiredattribute__work_structure=True, work_structure=self.work_model)|
            Q(requiredattribute__years_of_experience=True, years_of_experience=years_of_experience)|
            Q(requiredattribute__first_language=True, first_language=self.native_language)|
            Q(requiredattribute__secondary_language=True, additional_languages__id__in=additional_language_ids)|
            Q(requiredattribute__working_hours=True, availableday__in=AvailableDay.objects.filter(working_hours_query))|
            Q(requiredattribute__location=True, jobpost__country=self.country)|
            Q(requiredattribute__skills__id__in=skill_ids)
        )
        if start_date and end_date:
            job_matching_query = Q(job_matching_query, created_at__range=[start_date, end_date])
        jobs = Job.objects.filter(job_matching_query).only("id").distinct("id")
        if job_only:
            return jobs
        job_ids = jobs.values_list("id", flat=True)
        query = dict(job_id__in=job_ids)
        if by_talent_country:
            query["country"] = self.country
        return JobPost.objects.filter(**query).order_by("-id")

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
        if  required_attribute.years_of_experience and self.years_of_experience > (job.years_of_experience or 0):
            score -=1
        if required_attribute.business_models.count() > 0 and required_attribute.business_models.intersection(self.business_models.all()).count() == 0:
            score -= 1
        if required_attribute.minimum_education_level and not self.education_set.filter(level=job.minimum_education_level).exists():
            score -= 1

        if required_attribute.first_language and self.native_language != job.first_language:
            score -= 1
        if required_attribute.secondary_language and job.additional_languages.intersection(self.additional_languages.all()).count() == 0:
            score -= 1
        if required_attribute.work_structure and self.work_model != job.work_structure:
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


    def dashboard_charts(self):
        return {
            "applications": self.applications_made_chart(),
            "interviews": self.interviews_chart()
        }

    def role(self):
        from jobs.models import JobFilter
        job_filter = JobFilter.objects.filter(talent=self).first()
        if not job_filter:
            return None
        if not job_filter.role:
            return None
        return Role.objects.filter(name__icontains=job_filter.role).first()

    def notifications(self, viewed:Optional[bool]=None):
        from notification.models import Notification
        recipients_query = Q(recipient_users__id=self.user.id)
        group_query = Q(
            Q(recipient_groups__contains=[NotificationGroup.ALL_USERS.value]) |
            Q(recipient_groups__contains=[NotificationGroup.TALENTS.value])
        )
        notifications = Notification.objects.filter(
            recipients_query | group_query
        )

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
        if hasattr(self, "jobfilter"):
            self.jobfilter.hard_delete()
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
    name = models.CharField(max_length=128)
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
        return self.name

    def location(self):
        return f"{self.address}, {self.country}"

    def get_logo(self):
        if not self.logo:
            return
        return self.logo.url

    def total_hires(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        queryset = JobApplication.objects.filter(job_post__recruiter__business=self,
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
        from jobs.models import JobPost
        # open roles are job posts that are posted
        queryset = JobPost.objects.filter(
            recruiter__business=self,
            status=JobStatusType.POSTED.value
        )
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

        from jobs.models import JobApplication

        queryset = JobApplication.objects.filter(job_post__recruiter__business=self)

        if start_date and not end_date:
            queryset = queryset.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            queryset = queryset.filter(created_at__lte=end_date)
        elif start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        if role_id:
            queryset = queryset.filter(job_post__job__role_id=role_id)
        if client:
            queryset = queryset.filter(job_post__job__hiring_company_name=client)

        return queryset.distinct("applicant").count()

    def average_days_to_hire(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        queryset = JobApplication.objects.filter(
            recruiter__business=self,
            stage__phase=PhaseType.HIRED.value
        )
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

        return int(queryset.aggregate(value=Avg("days_to_hire"))["value"] or 0)

    def total_invitations_sent(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from chats.models import Message
        from jobs.models import JobPost
        job_post_ids = JobPost.objects.filter(recruiter__business=self).only("id").values_list("id", flat=True)
        queryset = Message.objects.filter(job_post_id__in=job_post_ids)
        if start_date and not end_date:
            queryset = queryset.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            queryset = queryset.filter(created_at__lte=end_date)
        elif start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        if role_id:
            queryset = queryset.filter(job_post__job__role_id=role_id)
        if client:
            queryset = queryset.filter(job_post__job__hiring_company_name=client)
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
                .filter(stage__phase=PhaseType.HIRED.value, recruiter__business=self)
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
        from jobs.models import JobApplication
        genders = GenderType.values()
        data_list = list()
        total_hires = self.total_hires(start_date, end_date, role_id, client)
        genders_aggregate = JobApplication.objects\
                .prefetch_related("applicant")\
                .filter(stage__phase=PhaseType.HIRED.value, recruiter__business=self)
        if start_date and not end_date:
            genders_aggregate = genders_aggregate.filter(stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            genders_aggregate = genders_aggregate.filter(stage_date_updated__lte=end_date)
        elif start_date and end_date:
            genders_aggregate = genders_aggregate.filter(stage_date_updated__range=[start_date, end_date])
        if role_id:
            genders_aggregate = genders_aggregate.filter(job_post__job__role_id=role_id)
        if client:
            genders_aggregate = genders_aggregate.filter(job_post__job__hiring_company_name=client)
        for gender in genders:
            data_list.append({
                "gender": gender,
                "count": genders_aggregate.filter(applicant__user__gender=gender).count(),
            })
        data_list = sorted(data_list, key=lambda x: x["count"], reverse=True)
        return (total_hires,
                data_list)

    def time_to_hire(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        data_list = JobApplication.objects.prefetch_related("job_post__job__role")\
        .filter(recruiter__business=self, stage__phase=PhaseType.HIRED.value)

        if start_date and not end_date:
            data_list = data_list.filter(stage_date_updated__gte=start_date)
        elif end_date and not start_date:
            data_list = data_list.filter(stage_date_updated__lte=end_date)
        elif start_date and end_date:
            data_list = data_list.filter(stage_date_updated__range=[start_date, end_date])
        if role_id:
            data_list = data_list.filter(job_post__job__role_id=role_id)
        if client:
            data_list = data_list.filter(job_post__job__hiring_company_name=client)

        data_list = data_list.values("job_post__job__role") \
            .annotate(
            role=F("job_post__job__role__name"),
            posted=Cast(Avg("posted_timeline"), output_field=IntegerField()),
            screening=Cast(Avg("screening_timeline"), output_field=IntegerField()),
            interview=Cast(Avg("interview_timeline"), output_field=IntegerField()),
            onboarding=Cast(Avg("onboarding_timeline"), output_field=IntegerField())
        )\
        .values("role", "posted",
                "screening", "interview", "onboarding")
        data_list = [dict(**data,
                          days_to_hire=sum([
                              data["posted"],
                              data["screening"],
                              data["interview"],
                              data["onboarding"],
                              ]
                          )) for data in  data_list]
        return sorted(data_list, key=lambda x: x["days_to_hire"], reverse=True)

    @staticmethod
    def job_role_stage_timeline(job_role_id, stages):
        from jobs.models import TalentApplicationStageTimeline

        stage_timelines = (
            TalentApplicationStageTimeline.objects.filter(job_role_id=job_role_id, stage__in=stages)
            .values("stage_id")
            .annotate(avg_timeline=Avg("timeline"))
        )

        stage_timeline_map = {item["stage_id"]: int(item["avg_timeline"] or 0) for item in stage_timelines}

        data_list = [
            {
                "stage": stage.name,
                "avg_timeline": stage_timeline_map.pop(stage.id, 0),
            }
            for stage in stages
        ]

        total_timeline = sum(item["avg_timeline"] for item in data_list)

        return {
            "graph": data_list,
            "days_to_hire": total_timeline,
        }

    def time_to_hire_via_stage(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import TalentApplicationStageTimeline
        from settings.models import WorkFlowStage
        stages = (
            WorkFlowStage.objects.filter(created_by__business=self)
            .order_by("order", "phase_order")
            .exclude(phase__in=(PhaseType.ONBOARDING, PhaseType.REJECTED))
        )
        timelines = TalentApplicationStageTimeline.objects.prefetch_related("application").filter(
                stage__created_by__business=self,
                application__stage__phase=PhaseType.HIRED.value,
            )
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
            )
            .distinct()
        )
        return [
            {
                "role": role["role_name"],
                **self.job_role_stage_timeline(role["role_id"], stages),
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
        from jobs.models import JobApplication
        ranges = (0, (1,2), (2,3), (3,4), 5)
        data_list = list()
        application = JobApplication.objects.filter(
            recruiter__business=self
        )
        if start_date and not end_date:
            application = application.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            application = application.filter(created_at__lte=end_date)
        elif start_date and end_date:
            application = application.filter(created_at__range=[start_date, end_date])
        if role_id:
            application = application.filter(job_post__job__role_id=role_id)
        if client:
            application = application.filter(job_post__job__hiring_company_name=client)
        applicants_ids = application.only("applicant_id").distinct("applicant_id").values_list("applicant_id", flat=True)
        applicants = Talent.objects.filter(id__in=applicants_ids).only("years_of_experience").distinct()

        for range_value in ranges:
            data = dict()
            data["years_of_experience"] = str(range_value if range_value == 0 else f"{range_value}+") if isinstance(range_value, int) else " - ".join(map(lambda x: str(x), range_value))
            if range_value == 0:
                data["count"] = applicants.filter(years_of_experience=0).count()
            elif isinstance(range_value, tuple):
                data["count"] = applicants.filter(years_of_experience__gte=range_value[0],
                                                  years_of_experience__lt=range_value[1]).count()
            else:
                data["count"] = applicants.filter(years_of_experience__gte=range_value).count()
            data_list.append(data)
        return data_list

    def talent_at_each_phase(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        application = JobApplication.objects.filter(
                recruiter__business=self,
                stage__isnull=False
        )
        if start_date and not end_date:
            application = application.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            application = application.filter(created_at__lte=end_date)
        elif start_date and end_date:
            application = application.filter(created_at__range=[start_date, end_date])
        if role_id:
            application = application.filter(job_post__job__role_id=role_id)
        if client:
            application = application.filter(job_post__job__hiring_company_name=client)
        phase = PhaseType.values()
        data_list = list()
        for phase in phase:
            data_list.append(
                {
                    "phase": phase,
                    "count": application.filter(stage__phase=phase).count()
                }
            )
        return sorted(data_list, key=lambda x: x["count"], reverse=True)

    def talent_at_each_stage(self, start_date:date=None, end_date:date=None, role_id: UUID=None, client: str=None):
        from jobs.models import JobApplication
        from settings.models import WorkFlowStage
        application = JobApplication.objects.filter(
                recruiter__business=self,
                stage__isnull=False
        )
        if start_date and not end_date:
            application = application.filter(created_at__gte=start_date)
        elif end_date and not start_date:
            application = application.filter(created_at__lte=end_date)
        elif start_date and end_date:
            application = application.filter(created_at__range=[start_date, end_date])
        if role_id:
            application = application.filter(job_post__job__role_id=role_id)
        if client:
            application = application.filter(job_post__job__hiring_company_name=client)
        stages = WorkFlowStage.objects.filter(created_by__business=self).order_by("order", "phase_order").only("id", "name")
        return [
            dict(
                stage=stage.name,
                count=application.filter(stage_id=stage.id).count()
            )
            for stage in stages
        ]

    def job_posts(self):
        from jobs.models import JobPost
        return JobPost.objects.filter(job__created_by__business=self)


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


class BusinessUser(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    added_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=100, choices=BusinessUserRoleType.choices(), blank=True)
    status = models.CharField(max_length=100, choices=BusinessUserStatusType.choices(),
                              default=BusinessUserStatusType.ACTIVE.value)

    def __str__(self) -> str:
        return str(self.user)

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
        self.status = BusinessUserStatusType.DELETED.value
        self.save(update_fields=["status"])
        self.delete()
        if hasattr(self, "businessusernotificationsettings"):
            self.businessusernotificationsettings.hard_delete()
        return




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


class TalentAvailableDay(BaseModel):
    talent = models.ForeignKey("Talent", on_delete=models.CASCADE)
    day = models.CharField(max_length=50, choices=Days.choices())
    end_time = models.TimeField(null=True)
    start_time = models.TimeField(null=True)


class CustomerCase(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255, choices=CaseReasonType.choices())
    subject = models.CharField(max_length=255)
    description = models.TextField()


class TalentFilter(BaseModel):
    business_user = models.OneToOneField("accounts.BusinessUser", on_delete=models.CASCADE)
    role = models.ForeignKey("accounts.Role", on_delete=models.SET_NULL, null=True)
    industry = models.ForeignKey("accounts.Industry", on_delete=models.SET_NULL, null=True)
    location = models.CharField(max_length=128, null=True)
    languages = models.ManyToManyField("core.Language")
    educational_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True)
    maximum_notice_period = models.PositiveSmallIntegerField(null=True)
    work_structure = models.CharField(max_length=100, choices=WorkStructureEnum.choices(), null=True)
    skills = models.ManyToManyField("accounts.Skill")

    def get_queryset(self, queryset=None):
        if not queryset:
            queryset = Talent.objects.all()
        if self.role:
            ids = Experience.objects.filter(role=self.role).only("talent_id").distinct("talent_id").values_list("talent_id", flat=True)
            queryset = queryset.filter(id__in=ids)
        if self.industry:
            queryset = queryset.filter(skills__department__industry=self.industry)
        if self.location:
            queryset = queryset.filter(Q(country__name__icontains=self.location)|
                                       Q(state__icontains=self.location)|Q(city__icontains=self.location))
        if self.languages.count() > 0:
            ids = self.languages.values_list("id", flat=True)
            queryset = queryset.filter(Q(native_language_id__in=ids)|
                                       Q(additional_languages__id__in=ids))
        if self.educational_level:
            ids = Education.objects.filter(level=self.educational_level).only("talent_id").distinct("talent_id").values_list("talent_id", flat=True)
            queryset = queryset.filter(id__in=ids)
        if self.work_structure:
            queryset = queryset.filter(work_model=self.work_structure)
        if self.skills.count() > 0:
            ids = self.skills.values_list("id", flat=True)
            queryset = queryset.filter(skills__id__in=ids)
        if self.maximum_notice_period:
            queryset = queryset.filter(notice_period__lte=self.maximum_notice_period)
        return queryset

    def results(self):
        return self.get_queryset().count()
