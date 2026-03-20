import string
from functools import cached_property

from accounts.enums import Days
from accounts.enums import Days
from accounts.enums import Days
from accounts.models import Talent, TalentAvailableDay
from accounts.models import Talent, TalentAvailableDay
from accounts.models import Talent, TalentAvailableDay
from core.enums import SalaryType
from core.enums import SalaryType
from core.enums import SalaryType
from core.models import BaseModel, Language
from core.models import BaseModel, Language
from core.models import BaseModel, Language
from django.db import models
from django.db.models import F, Q, Count, IntegerField, When, Case, Value
from django.db.models.functions import Coalesce, Now, Extract, Cast
from django.db.models.signals import pre_save
from django_softdelete.managers import SoftDeleteManager
from jobs.managers import JobManager
from settings.enums import PlaceHolderType
from settings.models import WorkFlowStage
from timezone_field import TimeZoneField

from helpers.loggers import Logger, LogSchema
from .db_functions import Epoch
from .enums import WorkStructureEnum, LunchBreakEnum, QuestionTypeEnum, PhaseType, WithdrawalFeedbackType, \
    JobStatusType, ScreeningResultStatusType


# Create your models here.
class EmploymentType(BaseModel):
    name = models.CharField(max_length=128)
    parent = models.ForeignKey("EmploymentType", on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(null=True)

    def __str__(self) -> str:
        return self.name

    def fullname(self):
        if self.parent:
            return f"{self.parent.name} ({self.name})"
        return self.name


class JobLevel(BaseModel):
    name = models.CharField(max_length=64)

    def __str__(self) -> str:
        return self.name

class AvailableDayManager(SoftDeleteManager):
    def bulk_create(self, objs, **kwargs):
        for obj in objs:
            pre_save.send(sender=self.model, instance=obj, created=False ,raw=False, using=self.db)
        return super().bulk_create(objs, **kwargs)
    
    def bulk_update(self, objs, *args, **kwargs):
        for obj in objs:
            pre_save.send(sender=self.model, instance=obj, created=True, raw=False, using=self.db)
        return super().bulk_update(objs, *args, **kwargs)
    

class AvailableDay(BaseModel):
    job = models.ForeignKey("Job", on_delete=models.CASCADE)
    day = models.CharField(max_length=32, choices=Days.choices())
    end_time = models.TimeField(null=True)
    start_time = models.TimeField(null=True)
    utc_start_time = models.TimeField(null=True)
    utc_end_time = models.TimeField(null=True)
    objects = AvailableDayManager()


class Job(BaseModel):
    PAID = "paid"
    UNPAID = "unpaid"
    LUNCH_BREAK_CHOICES = (
        (PAID, PAID),
        (UNPAID, UNPAID)
    )
    logo = models.ImageField(upload_to="jobs/logos", null=True, blank=True)
    created_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.SET_NULL, null=True) #TODO take care during delete account
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.SET_NULL, null=True)
    hiring_company_name = models.CharField(max_length=64, null=True)
    hiring_company_description = models.TextField(null=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    about = models.TextField(null=True)
    years_of_experience = models.IntegerField(null=True)
    minimum_education_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True)
    business_models = models.ManyToManyField("BusinessModel", blank=True)
    job_level = models.ForeignKey(JobLevel, on_delete=models.SET_NULL, null=True)
    qualification = models.TextField(null=True, blank=True)
    work_structure = models.CharField(choices=WorkStructureEnum.choices(), null=True, blank=True)
    first_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    additional_languages = models.ManyToManyField(Language, related_name="jobs", blank=True)
    office_address = models.CharField(max_length=128, null=True)
    lunch_break = models.CharField(max_length=50, choices=LunchBreakEnum.choices(), null=True)
    lunch_break_time = models.PositiveSmallIntegerField(default=0)
    responsibilities = models.TextField(null=True, blank=True)
    additional_hours_description = models.TextField(null=True)
    additional_skills = models.TextField(null=True)
    additional_hours_start = models.CharField(max_length=100, null=True, blank=True)
    additional_hours_end = models.CharField(max_length=100, null=True, blank=True)
    technological_requirement = models.CharField(max_length=100, null=True, blank=True)
    availability_timezone = TimeZoneField(default="America/Vancouver")
    flexible_availability = models.BooleanField(default=False)
    department = models.ForeignKey("accounts.Department", null=True, on_delete=models.SET_NULL)
    role = models.ForeignKey("accounts.Role", null=True, on_delete=models.SET_NULL)
    skills = models.ManyToManyField("accounts.Skill", blank=True)
    min_match_score = models.FloatField(null=True)
    objects = JobManager()

    required_attributes_keys = (
            "skills", "role", "job_level", "years_of_experience",
            "business_models", "minimum_education_level",
            "work_structure", "technological_requirement",
            "first_language", "secondary_language", "working_hours",
            "location"
        )

    @property
    def get_title(self):
        if not self.role:
            return "" if not self.title else self.title
        return self.role.name

    def get_work_structure(self):
        if not self.work_structure:
            return ""
        return str(self.work_structure).title()



    def get_availability(self, schema, query=None):
        data = list()
        for value in Days.values():
            availability = query.filter(day=value).first()
            if availability:
                data.append({
                    "day": value,
                    "availability": schema.from_orm(availability) if availability else None
                })
        return data

    def send_alerts(self):
        JobAlert.send_alerts(self)
        return


    @property
    def required_keys(self):
        if not hasattr(self, "requiredattribute"):
           return []
        attributes = self.requiredattribute
        data = []
        for attribute in self.required_attributes_keys:
            value = getattr(attributes, attribute)
            if attribute in ("skills", "business_models"):
                if value.count() > 0:
                    data.append(attribute)
            else:
                if value is True:
                    data.append(attribute)
        return data


    @property
    def non_required_keys(self):
        if not hasattr(self, "requiredattribute"):
           return []
        attributes = self.requiredattribute
        data = []
        for attribute in self.required_attributes_keys:
            value = getattr(attributes, attribute)
            if attribute in ("skills", "business_models"):
                if value.count() == 0:
                    data.append(attribute)
            else:
                if value is False:
                    data.append(attribute)
        return data


    def __str__(self) -> str:
        return f"{self.get_title}({self.uid})"

    def logo_url(self):
        if self.logo:
            return self.logo.url
        if not self.created_by:
            return
        if not self.created_by.business:
            return
        logo = self.created_by.business.get_logo()
        if not logo:
            return
        return logo



    def hiring_company(self):
        return self.hiring_company_name

    def business_logo(self):
        return self.created_by.business.get_logo()

    def business_name(self):
        if not self.created_by:
            return
        if not self.created_by.business:
            return
        return self.created_by.business.name

    def get_company(self):
        if not self.hiring_company_name:
            return self.business_name()
        return self.hiring_company()

    def availability_query(self):
        working_hours_query = Q()

        for availability in self.availableday_set.all():
            if not(availability.end_time and availability.start_time):
                continue
            day_query = Q(
                day=availability.day,
                start_time__lte=availability.end_time,
                end_time__gte=availability.start_time
            )
            working_hours_query |= day_query
        return working_hours_query

    def get_available_days(self):
        from jobs.schemas import JobAvailableDaySchema

        data = list()
        for value in Days.values():
            availability = self.availableday_set.filter(day=value).first()
            if availability:
                data.append({
                    "day": value,
                    "availability": JobAvailableDaySchema.from_orm(availability) if availability else None
                })
        return data

    def get_skills(self):
        from jobs.schemas import SkillSchema, JobSkillSchema
        from accounts.models import SkillCategory
        categories = SkillCategory.objects.only("id", "name")
        data = list()
        for category in categories:
            data.append(JobSkillSchema(
                category=category.name,
                skills=[SkillSchema.from_orm(skill) for skill in self.skills.filter(category_id=category.id)]
            ))
        return data


    def workflow_stage_data(self):
        from settings.models import WorkFlowStage
        business = self.created_by.business
        try:
            return (WorkFlowStage.objects.select_related("created_by__business").filter(created_by__business=business).
                    annotate(applications=Count('jobapplication', filter=Q(jobapplication__job_post__job=self, jobapplication__deleted_at__isnull=True),
                                                distinct=True)).order_by('phase_order', 'order')
                    .values("uid", "phase", "name", "applications"))
        except Exception as e:
            Logger.critical(LogSchema(title="Workflow stage data error", sender="job.workflow_stage_data",
                                      description=str(e), data=dict()).__dict__)
            return []


class JobPost(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    about = models.TextField(null=True)
    status = models.CharField(max_length=50, choices=JobStatusType.choices(), default=JobStatusType.DRAFT.value)
    date_posted = models.DateTimeField(null=True)
    posted_order = models.GeneratedField(
        expression=Coalesce(
            Cast(Epoch("date_posted"), IntegerField()),
            Value(0)
        ),
        output_field=models.IntegerField(),
        db_persist=True
    )
    country = models.ForeignKey("accounts.Country", on_delete=models.SET_NULL, null=True)
    province = models.ForeignKey("core.State", on_delete=models.SET_NULL, null=True)
    city = models.CharField(max_length=200, null=True)
    postal_code = models.CharField(max_length=20, null=True)
    benefits = models.JSONField(default=list, blank=True)
    share_compensation = models.BooleanField(default=True)
    salary_type = models.CharField(max_length=50, choices=SalaryType.choices(), default=SalaryType.ANNUALLY.value, null=True)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    salary_currency = models.ForeignKey(
        "core.Currency", 
        on_delete=models.SET_NULL, 
        related_name="jobs_posts_with_salary_currency",
        null=True,
    )
    salary_bonus_type = models.CharField(max_length=50, choices=SalaryType.choices(), default=SalaryType.ANNUALLY.value, null=True)
    salary_bonus_min = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    salary_bonus_max = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    salary_bonus_currency = models.ForeignKey(
        "core.Currency", 
        on_delete=models.SET_NULL, 
        related_name="jobs_posts_with_bonus_currency",
        null=True,
    )
    recruiter = models.ForeignKey(
        "accounts.BusinessUser", 
        null=True, 
        on_delete=models.SET_NULL, 
        related_name="recruiter"
    )
    posted_by = models.ForeignKey(
        "accounts.BusinessUser",
        null=True,
        on_delete=models.SET_NULL,
        related_name="posted_by",
        blank=True
    )
    last_refreshed = models.DateTimeField(null=True, default=None)
    refresh_order = models.GeneratedField(
        expression=Coalesce(
            Cast(Epoch("last_refreshed"), IntegerField()),
            Value(0)
        ),
        output_field=models.IntegerField(),
        db_persist=True
    )
    edited_by = models.ForeignKey("accounts.BusinessUser", related_name="edited_job_posts", on_delete=models.SET_NULL
                                  , null=True)
    edited_at = models.DateTimeField(null=True)
    
    promotion_code = models.CharField(max_length=200, null=True, blank=True)
    linkedin_tags = models.JSONField(default=list)


    def get_tags(self):
        return self.tags.values_list("name", flat=True)

    @cached_property
    def get_code(self, length=22):
        base = string.digits + string.ascii_letters
        num = self.uid.int
        chars = []
        while num:
            num, rem = divmod(num, 62)
            chars.append(base[rem])
        return ''.join(chars[::-1]).rjust(length, '0')

    def copy(self):
        return JobPost.objects.create(
            job=self.job,
            status=JobStatusType.DRAFT.value,
            country=self.country,
            province=self.province,
            city=self.city,
            postal_code=self.postal_code,
            benefits=self.benefits,
            share_compensation=self.share_compensation,
            salary_min=self.salary_min,
            salary_max=self.salary_max,
            salary_currency=self.salary_currency,
            salary_bonus_min=self.salary_bonus_min,
            salary_bonus_max=self.salary_bonus_max,
            salary_bonus_currency=self.salary_bonus_currency,
            recruiter=self.recruiter,
            posted_by=self.posted_by,
        )

    def get_location(self):
        data = list()
        if self.city:
            data.append(self.city)
        if self.province:
            data.append(self.province.name)
        if self.country:
            data.append(self.country.name)
        return ", ".join(data)




    def __str__(self) -> str:
        return f"{self.job}({self.country})"


    def get_country(self):
        if not self.country:
            return
        return self.country.name

    def get_province(self):
        if not self.province:
            return
        return self.province.name
    
    def get_about(self):
        if not self.job.about:
            return self.about
        return self.job.about
    
    

    def get_city(self):
        return self.city

    def get_talents(self, queryset=None):
        from jobs.queries import add_talent_match_score
        if not queryset:
            queryset = Talent.objects.filter(visible=True)
        return add_talent_match_score(queryset, self).filter(computed_match_score__gte=50).order_by("-computed_match_score")

    def phase_data(self):
        def get_phase_count():
            phase_dt = list(filter(lambda x: x["stage_phase"] == phase, data_set))
            return phase_dt[0]["count"] if len(phase_dt) > 0 else 0
        applications = self.jobapplication_set
        data = [
            {"key": "applicants", "count": applications.count()},
            {"key": "new", "count": applications.filter(Q(stage__isnull=True)| Q(stage__phase=PhaseType.NEW.value)).count()},
        ]
        data_set = applications.filter(stage__isnull=False).values("stage__phase")\
            .annotate(count=models.Count("stage__phase"),
                     stage_phase=F("stage__phase"))\
            .order_by("stage_phase").values("stage_phase", "count")
        for phase in PhaseType.values():
            data.append({
                "key": phase,
                "count": get_phase_count()
            })
        return data

    def workflow_stage_data(self):
        from settings.models import WorkFlowStage
        try:
            business = self.job.created_by.business
            return (WorkFlowStage.objects.select_related("created_by__business").filter(created_by__business=business).
                    annotate(applications=Count("jobapplication", filter=Q(jobapplication__job_post=self, jobapplication__deleted_at__isnull=True),
                                                distinct=True)).order_by('phase_order', 'order')
                    .values("uid", "phase", "name", "applications")
                    )
        except Exception as e:
            Logger.critical(LogSchema(title="Workflow stage data error", sender="jobpost.workflow_stage_data",
                                      description=str(e), data=dict()).__dict__)
            return []

    def view(self):
        metric, _ = JobPostMetrics.objects.get_or_create(job_post=self)
        metric.weekly_views = F("weekly_views") + 1
        metric.save()
        return

    def update_email_share(self):
        metric, _ = JobPostMetrics.objects.get_or_create(job_post=self)
        metric.daily_email_shares = F("daily_email_shares") + 1
        metric.save()
        return

    def get_data(self, talent, weak=True):
        from .schemas import JobAvailableDaySchema
        job = self.job
        if not hasattr(job, "requiredattribute"):
            data = dict(
                skills = None,
                business_models = None,
                role = None,
                job_level = None,
                years_of_experience = None,
                minimum_education_level = None,
                work_structure = None,
                first_language = None,
                secondary_language = None,
                working_hours = None,
                location = None,
            )
            return data

        attributes = job.requiredattribute
        non_negotiables = job.required_keys
        data = dict()
        total_score = attributes.total_score()
        score = total_score
        for attribute in non_negotiables:
            if attribute == "skills":
                skills = attributes.skills.intersection(talent.skills.all())
                skill_count = skills.count()
                if skill_count == 0:
                    score -= 1
                    skills = attributes.skills.all()
                if (skill_count == 0 and weak is True) or (skill_count > 0 and weak is False):
                    data["skills"]= RequiredAttribute.format_skills_under_category(skills)  if skills.count() > 0 else None
            elif attribute == "business_models":
                business_models = attributes.business_models.intersection(talent.business_models.all())
                bm_count = business_models.count()
                if bm_count == 0:
                    score -= 1
                    business_models = attributes.business_models.all()
                if (bm_count == 0 and weak is True) or (bm_count > 0 and weak is False):
                    data["business_models"] = business_models if business_models.count() > 0 else None

            elif attribute == "role":
                experiences = talent.experience_set.filter(role=job.role).count()
                if experiences == 0:
                    score -= 1
                if (experiences > 0 and weak is False) or (experiences == 0 and weak is True):
                    data["role"] = job.role

            elif attribute == "job_level":
                experiences = talent.experience_set.filter(level=job.job_level).count()
                if experiences == 0:
                    score -= 1
                if (experiences > 0 and weak is False) or (experiences == 0 and weak is True):
                    data["job_level"] = job.job_level

            elif attribute == "years_of_experience":
                fits = talent.years_of_experience > (job.years_of_experience or  0)
                if not fits:
                    score -= 1
                if (fits and weak is False) or (not fits and weak is True):
                    data["years_of_experience"] = talent.years_of_experience

            elif attribute == "minimum_education_level":
                education = talent.education_set.filter(level=job.minimum_education_level).count()
                if education == 0:
                    score -= 1
                if (education > 0 and weak is False) or (education == 0 and weak is True):
                    data["minimum_education_level"] = job.minimum_education_level
            elif attribute == "work_structure":
                fits = job.work_structure in talent.work_models
                if not fits:
                    score -= 1
                if (fits and weak is False) or (not fits and weak is True):
                    data["work_structure"]  = job.work_structure

            # elif attribute == "technological_requirement":
            #     if weak is False:
            #         data["technological_requirement"] = self.technological_requirement

            elif attribute == "first_language":
                fits = talent.native_language == job.first_language
                if not fits and job.first_language:
                    score -= 1
                if (fits and weak is False) or (not fits and weak is True):
                    data["first_language"] = job.first_language

            elif attribute == "secondary_language":
                languages = job.additional_languages.all().intersection(talent.additional_languages.all())
                language_count = languages.count()
                if language_count == 0:
                    score -= 1
                    languages = job.additional_languages.all()
                if (language_count > 0 and weak is False) or (language_count == 0 and weak is True):
                    data["secondary_language"] = languages if languages.count() > 0 else None

            elif attribute == "location":
                fits = self.country == talent.country
                if not fits and self.country:
                    score -= 1
                if (fits and weak is False) or (not fits and weak is True):
                    data["location"] = talent.country

            elif attribute == "working_hours":
                talent_wh_query = talent.availability_query()
                wh_query = job.availableday_set.filter(talent_wh_query)
                wh_count = wh_query.count()
                if wh_count == 0:
                    score -= 1
                    wh_query = job.availableday_set.all()
                if (wh_count > 0 and weak is False) or (wh_count == 0 and weak is True):
                    data["working_hours"] = job.get_availability(JobAvailableDaySchema, wh_query) if wh_query.count() > 0 else None
        return data

    def weakness(self, talent):
        return self.get_data(talent, weak=True)


    def strength(self, talent):
        return self.get_data(talent, weak=False)


    def non_negotiable(self):
        from .schemas import JobAvailableDaySchema
        job = self.job
        if not hasattr(job, "requiredattribute"):
            return dict(
                skills = None,
                business_models = None,
                role = None,
                job_level = None,
                years_of_experience = None,
                minimum_education_level = None,
                work_structure = None,
                first_language = None,
                secondary_language = None,
                working_hours = None,
                location = None,
            )

        attributes = job.requiredattribute
        non_negotiables = job.required_keys
        data = dict()
        for attribute in non_negotiables:
            if attribute == "skills":
                if attributes.skills.count() > 0:
                    data["skills"] = RequiredAttribute.format_skills_under_category(attributes.skills.all())
            elif attribute == "business_models":
                if attributes.business_models.count() > 0:
                    data["business_models"] = attributes.business_models.all() if attributes.business_models.count() > 0 else None

            elif attribute == "role":
                data["role"] = job.role

            elif attribute == "job_level":
                data["job_level"] = job.job_level

            elif attribute == "years_of_experience":
                data["years_of_experience"] = job.years_of_experience

            elif attribute == "minimum_education_level":
                data["minimum_education_level"] = job.minimum_education_level
            elif attribute == "work_structure":
                data["work_structure"] = job.work_structure

            # elif attribute == "technological_requirement":
            #     data["technological_requirement"] = job.technological_requirement

            elif attribute == "first_language":
                data["first_language"] = job.first_language

            elif attribute == "secondary_language":
                data["secondary_language"] = job.additional_languages.all() if job.additional_languages.count() > 0 else None

            elif attribute == "location":
                data["location"] = self.country

            elif attribute == "working_hours":
                data["working_hours"] = job.get_availability(JobAvailableDaySchema, job.availableday_set.all()) if job.availableday_set.count() > 0 else None
        return data

    def screening_questions(self):
        return self.job.screeningquestion_set.all()

    def match_score(self, talent):
        from jobs.queries import add_job_post_annotations
        job_post = add_job_post_annotations(JobPost.objects.filter(id=self.id), talent)
        if job_post.exists():
            return job_post.first().computed_match_score
        return 0

    def invited(self, talent):
        return JobInvite.objects.filter(job=self.job, talent=talent).exists()

class JobPostTag(BaseModel):
    business = models.ForeignKey("accounts.Business", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    job_posts = models.ManyToManyField(JobPost, related_name="tags", blank=True)


class JobPostMetrics(BaseModel):
    job_post = models.OneToOneField(JobPost, on_delete=models.CASCADE, null=True)
    daily_email_shares = models.PositiveIntegerField(default=0)
    weekly_views = models.PositiveIntegerField(default=0)


    def reset_daily_email_shares(self):
        self.daily_email_shares = 0
        self.save()

    def reset_weekly_views(self):
        self.weekly_views = 0
        self.save()

class JobInvite(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE)

class JobApplication(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, null=True)
    applicant = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE)
    available_for_schedule = models.BooleanField(default=True)
    recruiter = models.ForeignKey(
        "accounts.BusinessUser",
        null=True,
        on_delete=models.SET_NULL
    )
    stage = models.ForeignKey("settings.WorkflowStage", on_delete=models.SET_NULL, null=True)
    stage_date_updated = models.DateTimeField(null=True)

    def other_application(self):
        if not self.stage:
            return
        if not self.stage.created_by:
            return
        if not self.stage.created_by.business:
            return
        return JobApplication.objects.select_related("stage__created_by").\
        filter(stage__created_by__business=self.stage.created_by.business, applicant=self.applicant).exclude(id=self.id).last()

    @cached_property
    def match(self):
        return self.applicant.job_match_score(self.job_post)

    def get_country(self):
        if not self.applicant:
            return
        if not self.applicant.country:
            return
        return self.applicant.country.name

    def placeholders_mapper(self, placeholder:str, external_recruiter=None):
        recruiter = self.recruiter if not external_recruiter else external_recruiter
        if placeholder == PlaceHolderType.YOUR_COMPANY_NAME.value:
            if not recruiter:
                return ""
            return recruiter.business.name
        elif placeholder == PlaceHolderType.CANDIDATE_FULLNAME.value:
            if not self.applicant:
                return ""
            return self.applicant.user.fullname
        elif placeholder == PlaceHolderType.JOB_APPLIED_TO.value:
            if not self.job_post:
                return ""
            return self.job_post.job.get_title
        elif placeholder == PlaceHolderType.CANDIDATE_FIRST_NAME.value:
            if not self.applicant:
                return ""
            return self.applicant.user.first_name
        elif placeholder == PlaceHolderType.YOUR_FIRST_NAME.value:
            if not recruiter:
                return ""
            return recruiter.user.first_name
        elif placeholder == PlaceHolderType.CANDIDATE_PHONE_NUMBER.value:
            if not self.applicant:
                return ""
            return self.applicant.user.get_phone()
        elif placeholder == PlaceHolderType.YOUR_FULL_NAME.value:
            if not recruiter:
                return ""
            return recruiter.user.fullname
        else:
            return ""

    def invited(self):
        return JobInvite.objects.filter(job=self.job_post.job, talent=self.applicant).exists()

    def get_email_context(self, external_recruiter=None)->dict:
        if not self.stage:
            return dict()
        if not self.stage.email_template:
            return dict()
        # lets retrieve the placeholders associated with the template attached to the stage
        stage_placeholders = self.stage.email_template.placeholders

        # lets get the function that converts a placeholder to a key that can be used in dictionary
        key_converter = self.stage.email_template.convert_placeholder_to_key

        # lets create a dictionary where the key is the placeholder and the value is the value retrieved from the placeholders_mapper function
        return {key_converter(placeholder):self.placeholders_mapper(placeholder, external_recruiter) for placeholder in stage_placeholders}

    def knockout(self):
        if not ScreeningQuestion.objects.filter(job=self.job_post.job, is_knockout=True).exists():
            return False
        return Answer.objects.filter(application=self, question__is_knockout=True, options__is_accepted=False).exists()


    def get_screening_result_status(self):
        if not ScreeningQuestion.objects.filter(job=self.job_post.job).exists():
            return None
        if self.knockout():
            return ScreeningResultStatusType.FAIL.value
        return ScreeningResultStatusType.PASS.value






    def __str__(self) -> str:
        return f"{self.job_post} ({self.applicant})"



class TalentApplicationStageTimeline(BaseModel):
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    job_role = models.ForeignKey("accounts.Role", on_delete=models.CASCADE)
    stage = models.ForeignKey("settings.WorkflowStage", on_delete=models.CASCADE)
    exit_date = models.DateTimeField(null=True)

    @staticmethod
    def add_time_spent_annotation(queryset):
        return queryset.annotate(days=Extract(Coalesce(F('exit_date'), Now()) - F('created_at')
    , 'epoch')).annotate(time_spent=Case(When(days__isnull=True, then=float(0)),
    default=F('days')/86400.0, output_field=IntegerField()))

    @staticmethod
    def add_time_spent_annotation_for_stages(queryset):
        return queryset.annotate(days=Extract(Coalesce(F('talentapplicationstagetimeline__exit_date'), Now()) - F('talentapplicationstagetimeline__created_at')
      , 'epoch')).annotate(time_spent=Case(When(days__isnull=True, then=float(0)),
            default=F('days') / 86400.0, output_field=IntegerField()))


class SavedJob(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, null=True)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, null=True)

    def __str__(self) -> str:
        return f"{self.job_post} ({self.talent.user})"


class JobDraft(BaseModel):
    user = models.OneToOneField("accounts.BusinessUser", on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)

class ScreeningQuestion(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=QuestionTypeEnum.choices())
    text = models.TextField()
    is_knockout = models.BooleanField(default=False)

    def options(self):
        return QuestionOption.objects.filter(question=self)

class QuestionOption(BaseModel):
    question = models.ForeignKey(ScreeningQuestion, on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False)
    text = models.CharField(max_length=128, null=True)

class Answer(BaseModel):
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    question = models.ForeignKey(ScreeningQuestion, on_delete=models.CASCADE, null=True)
    options = models.ManyToManyField(QuestionOption)
    text = models.TextField(null=True)
    files = models.JSONField(default=list, null=True)


class RequiredSecondaryLanguage(BaseModel):
    required_attribute = models.ForeignKey("RequiredAttribute", on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)


class RequiredSkill(BaseModel):
    required_attribute = models.ForeignKey("RequiredAttribute", on_delete=models.CASCADE, related_name="required_skills")
    skill = models.ForeignKey("accounts.Skill", on_delete=models.CASCADE)


class RequiredAttribute(BaseModel):
    job = models.OneToOneField(Job, on_delete=models.CASCADE)
    role = models.BooleanField(default=False)
    job_level = models.BooleanField(default=False)
    years_of_experience = models.BooleanField(default=False)
    business_models = models.ManyToManyField("BusinessModel", blank=True)
    minimum_education_level = models.BooleanField(default=False)
    work_structure = models.BooleanField(default=False)
    technological_requirement = models.BooleanField(default=False)
    first_language = models.BooleanField(default=False)
    secondary_language = models.BooleanField(default=False)
    working_hours = models.BooleanField(default=False)
    location = models.BooleanField(default=False)
    secondary_languages = models.ManyToManyField(Language, through=RequiredSecondaryLanguage)
    skills = models.ManyToManyField("accounts.Skill", through=RequiredSkill, related_name="required_attribute")

    def __str__(self) -> str:
        return f"{self.job}({self.uid})"

    def total_score(self):
        score = 1
        if self.skills.count() > 0:
            score += 1
        if self.role:
            score += 1
        if self.job_level:
            score += 1
        if self.years_of_experience:
            score += 1
        if self.business_models.count() > 0:
            score += 1
        if self.minimum_education_level:
            score += 1
        if self.first_language:
            score += 1
        if self.secondary_language:
            score += 1
        if self.working_hours:
            score += 1
        if self.location:
            score += 1
        return score

    @staticmethod
    def format_skills_under_category(skills):
        from jobs.schemas import SkillSchema, JobSkillSchema
        from accounts.models import SkillCategory, Skill
        categories = SkillCategory.objects.only("id", "name")
        skill_ids = skills.values_list("id", flat=True)
        data = list()
        for category in categories:
            data.append(JobSkillSchema(
                category=category.name,
                skills=[SkillSchema.from_orm(skill) for skill in Skill.objects.filter(id__in=skill_ids, category_id=category.id)]
            ))
        return data

    def get_skills(self):
        return self.format_skills_under_category(self.skills)


class JobApplicationWithdrawal(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, null=True, default=None)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, null=True)
    feedback_type = models.PositiveSmallIntegerField(default=0)
    feedback = models.TextField()

    @staticmethod
    def feedback_type_to_number(feedback_type: WithdrawalFeedbackType):
        data = {
            WithdrawalFeedbackType.SKILLS.name: 0,
            WithdrawalFeedbackType.JOB_OFFER.name: 1,
            WithdrawalFeedbackType.WORK_HOURS.name: 2,
            WithdrawalFeedbackType.COMPENSATION.name: 3
        }
        return data.get(feedback_type.name, 4)

    @staticmethod
    def number_to_feedback(number:int):
        data = {
            0: WithdrawalFeedbackType.SKILLS.value,
            1: WithdrawalFeedbackType.JOB_OFFER.value,
            2: WithdrawalFeedbackType.WORK_HOURS.value,
            3: WithdrawalFeedbackType.COMPENSATION.value,
            4: WithdrawalFeedbackType.OTHERS.value
        }
        return data.get(number)

class JobInterview(BaseModel):
    application = models.ForeignKey("jobs.JobApplication", models.CASCADE)

class BusinessModel(BaseModel):
    name = models.CharField(max_length=64)
    description = models.TextField()

    def __str__(self) -> str:
        return self.name


class JobAlert(BaseModel):
    talent = models.OneToOneField(Talent, on_delete=models.CASCADE)
    jobs = models.ManyToManyField(Job)



    @classmethod
    def send_alerts(cls, job):

        from notification.notifications import send_job_alert_notification
        user_ids = (cls.objects.filter(jobs__jobpost__status=JobStatusType.POSTED.value).filter(
            Q(jobs__employment_type=job.employment_type)|
            Q(jobs__years_of_experience=job.years_of_experience)|
            Q(jobs__minimum_education_level=job.minimum_education_level)|
            Q(jobs__job_level=job.job_level)|
            Q(jobs__first_language=job.first_language)|
            Q(jobs__flexible_availability=job.flexible_availability)|
            Q(jobs__department=job.department)|
            Q(jobs__role=job.role)|
            Q(jobs__min_match_score = job.min_match_score)|
            Q(jobs__skills__id__in=job.skills.all().values_list("id", flat=True))|
            Q(jobs__business_models__id__in=job.business_models.all().values_list("id", flat=True)))
         .distinct("talent__user_id").values_list("talent__user_id", flat=True))
        send_job_alert_notification(job, user_ids)
        return


class JobPostExport(BaseModel):
    file = models.FileField(upload_to="job-post-export")

