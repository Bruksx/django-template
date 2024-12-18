from django.db import models, transaction
from django.db.models import F, Q
from timezone_field import TimeZoneField

from accounts.enums import Days
from accounts.models import Talent, TalentAvailableDay
from core.models import BaseModel, Language
from settings.enums import PlaceHolderType
from .enums import WorkStructureEnum, LunchBreakEnum, QuestionTypeEnum, PhaseType, WithdrawalFeedbackType, \
    JobStatusType
from .managers import JobManager


# Create your models here.
class EmploymentType(BaseModel):
    name = models.CharField(max_length=128)
    parent = models.ForeignKey("EmploymentType", on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(null=True)

    def __str__(self) -> str:
        return self.name


class JobLevel(BaseModel):
    name = models.CharField(max_length=64)

    def __str__(self) -> str:
        return self.name
    

class Qualification(BaseModel):
    name = models.CharField(max_length=64)

    def __str__(self) -> str:
        return self.name


class AvailableDay(BaseModel):
    job = models.ForeignKey("Job", on_delete=models.CASCADE)
    day = models.CharField(max_length=32, choices=Days.choices())
    end_time = models.TimeField(null=True)
    start_time = models.TimeField(null=True)


class Job(BaseModel):
    PAID = "paid"
    UNPAID = "unpaid"
    LUNCH_BREAK_CHOICES = (
        (PAID, PAID),
        (UNPAID, UNPAID)
    )
    logo = models.ImageField(upload_to="jobs/logos", null=True, blank=True)
    created_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.SET_NULL, null=True)
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.SET_NULL, null=True)
    hiring_company_name = models.CharField(max_length=64, null=True)
    hiring_company_description = models.TextField(null=True)
    title = models.CharField(max_length=32, null=True)
    about = models.TextField(null=True)
    years_of_experience = models.IntegerField(null=True)
    minimum_education_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True)
    business_models = models.ManyToManyField("BusinessModel")
    job_level = models.ForeignKey(JobLevel, on_delete=models.SET_NULL, null=True)
    qualification = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)
    work_structure = models.CharField(choices=WorkStructureEnum.choices(), null=True)
    first_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    additional_languages = models.ManyToManyField(Language, related_name="jobs")
    office_address = models.CharField(max_length=128)
    lunch_break = models.CharField(max_length=16, choices=LunchBreakEnum.choices())
    lunch_break_time = models.PositiveSmallIntegerField(default=0)
    responsibilities = models.JSONField(default=list)
    additional_hours_description = models.TextField(null=True)
    additional_hours_start = models.TimeField(null=True)
    additional_hours_end = models.TimeField(null=True)
    technological_requirement = models.CharField(max_length=16, null=True)
    availability_timezone = TimeZoneField(default="America/Vancouver")
    flexible_availability = models.BooleanField(default=False)
    department = models.ForeignKey("accounts.Department", null=True, on_delete=models.SET_NULL)
    role = models.ForeignKey("accounts.Role", null=True, on_delete=models.SET_NULL)
    skills = models.ManyToManyField("accounts.Skill")

    objects = JobManager()

    def __str__(self) -> str:
        return f"{self.title}({self.uid})"

    def logo_url(self):
        return self.logo.url if self.logo else self.created_by.business.get_logo()

    def business_logo(self):
        return self.created_by.business.get_logo()

    def business_name(self):
        return self.created_by.business.name

    def availability_query(self):
        working_hours_query = Q()

        for availability in self.availableday_set.all():
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




class JobPost(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=JobStatusType.choices(), default=JobStatusType.DRAFT.value)
    date_posted = models.DateTimeField(null=True)
    country = models.ForeignKey("accounts.Country", on_delete=models.SET_NULL, null=True)
    province = models.CharField(max_length=64, null=True)
    postal_code = models.CharField(max_length=8, null=True)
    benefits = models.JSONField(default=list)
    share_compensation = models.BooleanField(default=True)
    annual_salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    annual_salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    annual_salary_currency = models.ForeignKey(
        "core.Currency", 
        on_delete=models.SET_NULL, 
        related_name="jobs_posts_with_salary_currency",
        null=True,
    )
    annual_bonus_min = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    annual_bonus_max = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    annual_bonus_currency = models.ForeignKey(
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
        related_name="posted_by"
    )


    def __str__(self) -> str:
        return f"{self.job}({self.country})"

    def get_talents(self):
        query = None

        def get_query(new_query):
            if not query:
                return new_query
            return query | new_query

        job = self.job
        if not hasattr(job, "requiredattribute"):
            talents = Talent.objects.select_related("user")
            if query:
                talents = talents.filter(query)
            return talents.distinct()

        required_attribute = job.requiredattribute
        if required_attribute.skills.count() > 0:
            ids = required_attribute.skills.values_list("id", flat=True)
            query = get_query(Q(skills__id__in=ids))
        if required_attribute.role and job.role:
            query = get_query(Q(experience__role=job.role))
        if required_attribute.job_level and job.job_level:
            query = get_query(Q(experience__level=job.job_level))
        if required_attribute.years_of_experience:
            query = get_query(Q(years_of_experience__gte=job.years_of_experience))
        if required_attribute.business_models.count() > 0:
            ids = required_attribute.business_models.values_list("id", flat=True)
            query = get_query(Q(business_models__id__in=ids))
        if required_attribute.minimum_education_level and job.minimum_education_level:
            query = get_query(Q(education__level=job.minimum_education_level))
        if required_attribute.first_language:
            query = get_query(Q(native_language=job.first_language))
        if required_attribute.secondary_language and job.additional_languages.count() > 0:
            ids = job.additional_languages.values_list("id", flat=True)
            query = get_query(Q(additional_languages__id__in=ids))
        if required_attribute.working_hours:
            query = get_query(Q(talentavailableday__id__in=TalentAvailableDay.objects.filter(job.availability_query()).only("id").values_list("id", flat=True)))
        if required_attribute.location:
            query = get_query(Q(country=self.country))
        talents =Talent.objects.select_related("user")
        if query:
            talents = talents.filter(query)
        return talents.distinct()

    def phase_data(self):
        def get_phase_count():
            phase_dt = list(filter(lambda x: x["stage_phase"] == phase, data_set))
            return phase_dt[0]["count"] if len(phase_dt) > 0 else 0
        applications = self.jobapplication_set
        data = [
            {"key": "applicants", "count": applications.count()},
            {"key": "new", "count": applications.filter(stage__isnull=True).count()},
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

    def view(self):
        metric, _ = JobPostMetrics.objects.get_or_create(job=self)
        metric.weekly_views = F("weekly_views") + 1
        metric.save()
        return

    def update_email_share(self):
        metric, _ = JobPostMetrics.objects.get_or_create(job_post=self)
        metric.daily_email_shares = F("daily_email_shares") + 1
        metric.save()
        return

class JobPostMetrics(BaseModel):
    job_post = models.OneToOneField(JobPost, on_delete=models.SET_NULL, null=True)
    daily_email_shares = models.PositiveIntegerField(default=0)
    weekly_views = models.PositiveIntegerField(default=0)


    def reset_daily_email_shares(self):
        self.daily_email_shares = 0
        self.save()

    def reset_weekly_views(self):
        self.weekly_views = 0
        self.save()


class JobApplication(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.SET_NULL, null=True)
    applicant = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE)
    recruiter = models.ForeignKey(
        "accounts.BusinessUser",
        null=True,
        on_delete=models.SET_NULL
    )
    stage = models.ForeignKey("settings.WorkflowStage", on_delete=models.SET_NULL, null=True)
    match = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    posted_timeline = models.PositiveSmallIntegerField(default=0)
    screening_timeline = models.PositiveSmallIntegerField(default=0)
    interview_timeline = models.PositiveSmallIntegerField(default=0)
    onboarding_timeline = models.PositiveSmallIntegerField(default=0)
    days_to_hire = models.GeneratedField(
        expression=F("posted_timeline") + F("screening_timeline") + F("interview_timeline") + F("onboarding_timeline"),
        output_field=models.PositiveIntegerField(),
        db_persist=True,
    )
    stage_date_updated = models.DateTimeField(null=True)


    def placeholders_mapper(self, placeholder:str):
        if placeholder == PlaceHolderType.YOUR_COMPANY_NAME.value:
            if not self.recruiter:
                return ""
            return self.recruiter.business.name
        elif placeholder == PlaceHolderType.CANDIDATE_FULLNAME.value:
            if not self.applicant:
                return ""
            return self.applicant.user.fullname
        elif placeholder == PlaceHolderType.JOB_APPLIED_TO.value:
            if not self.job_post:
                return ""
            return self.job_post.job.title
        elif placeholder == PlaceHolderType.CANDIDATE_FIRST_NAME.value:
            if not self.applicant:
                return ""
            return self.applicant.user.first_name
        elif placeholder == PlaceHolderType.YOUR_FIRST_NAME.value:
            if not self.recruiter:
                return ""
            return self.recruiter.user.first_name
        elif placeholder == PlaceHolderType.CANDIDATE_PHONE_NUMBER.value:
            if not self.applicant:
                return ""
            return self.applicant.user.phone_number
        else:
            return ""


    def get_email_context(self):
        if not self.stage:
            return dict()
        if not self.stage.email_template:
            return dict()
        stage_placeholders = self.stage.email_template.placeholders
        key_converter = self.stage.email_template.convert_placeholder_to_key
        return {key_converter(placeholder):self.placeholders_mapper(placeholder) for placeholder in stage_placeholders}

    def knockout(self):
        return Answer.objects.filter(application=self, question__is_knockout=True, options__is_accepted=False).exists()


    def __str__(self) -> str:
        return f"{self.job_post} ({self.applicant})"



class TalentApplicationStageTimeline(BaseModel):
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    job_role = models.ForeignKey("accounts.Role", on_delete=models.CASCADE)
    stage = models.ForeignKey("settings.WorkflowStage", on_delete=models.CASCADE)
    timeline = models.PositiveSmallIntegerField(default=0)


class SavedJob(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, null=True)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, null=True)

    def __str__(self) -> str:
        return f"{self.job_post} ({self.user})"


class JobDraft(BaseModel):
    user = models.OneToOneField("accounts.BusinessUser", on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)


class JobFilter(BaseModel):
    talent = models.OneToOneField("accounts.Talent", on_delete=models.CASCADE, null=True)
    role = models.CharField(max_length=100, default="", blank=True)
    years_of_experience = models.PositiveSmallIntegerField(default=1)
    office_location = models.ForeignKey("accounts.Country", on_delete=models.SET_NULL, null=True)
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey("accounts.Department", on_delete=models.SET_NULL, null=True)
    minimum_education_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True)
    location_type = models.CharField(choices=WorkStructureEnum.choices(), default=WorkStructureEnum.IN_OFFICE.value)
    remove_applied_jobs = models.BooleanField(default=False)


    def get_queryset(self, queryset):
        # queryset for job posts
        if self.years_of_experience > 0:
            queryset = queryset.filter(job__years_of_experience=self.years_of_experience)
        if self.office_location:
            queryset = queryset.filter(country=self.office_location)
        if self.employment_type:
            queryset = queryset.filter(job__employment_type=self.employment_type)
        if self.department:
            queryset = queryset.filter(job__department=self.department)
        if self.minimum_education_level:
            queryset = queryset.filter(job__minimum_education_level=self.minimum_education_level)
        if self.location_type:
            queryset = queryset.filter(job__work_structure=self.location_type)
        if self.remove_applied_jobs:
            queryset = queryset.exclude(jobapplication__applicant=self.talent)
        if self.role:
            queryset = queryset.filter(job__role__name__icontains=self.role)
        return queryset

class ScreeningQuestion(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    type = models.CharField(max_length=16, choices=QuestionTypeEnum.choices())
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

class RequiredAttribute(BaseModel):
    job = models.OneToOneField(Job, on_delete=models.CASCADE)
    skills = models.ManyToManyField("accounts.Skill")
    role = models.BooleanField(default=False)
    job_level = models.BooleanField(default=False)
    years_of_experience = models.BooleanField(default=False)
    business_models = models.ManyToManyField("BusinessModel")
    minimum_education_level = models.BooleanField(default=False)
    work_structure = models.BooleanField(default=False)
    technological_requirement = models.BooleanField(default=False)
    first_language = models.BooleanField(default=False)
    secondary_language = models.BooleanField(default=False)
    working_hours = models.BooleanField(default=False)
    location = models.BooleanField(default=False)

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


class JobApplicationWithdrawal(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.SET_NULL, null=True, default=None)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.SET_NULL, null=True)
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
