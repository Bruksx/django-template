from django.db import models
from timezone_field import TimeZoneField

from accounts.enums import Days
from core.models import BaseModel, Language
from .enums import WorkStructureEnum, LunchBreakEnum, QuestionTypeEnum, StageType
from .managers import JobManager


# Create your models here.
class EmploymentType(BaseModel):
    name = models.CharField(max_length=128)
    parent = models.ForeignKey("EmploymentType", on_delete=models.DO_NOTHING, null=True, blank=True)
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
    job = models.ForeignKey("Job", on_delete=models.DO_NOTHING)
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
    created_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.DO_NOTHING, null=True)
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.SET_NULL, null=True)
    hiring_company_name = models.CharField(max_length=64, null=True)
    hiring_company_description = models.TextField(null=True)
    title = models.CharField(max_length=32, null=True)
    about = models.TextField(null=True)
    years_of_experience = models.IntegerField(null=True)
    minimum_education_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.DO_NOTHING, null=True)
    business_models = models.ManyToManyField("BusinessModel")
    job_level = models.ForeignKey(JobLevel, on_delete=models.DO_NOTHING, null=True)
    qualification = models.ForeignKey(Qualification, on_delete=models.DO_NOTHING, null=True)
    work_structure = models.CharField(choices=WorkStructureEnum.choices(), null=True)
    first_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    additional_languages = models.ManyToManyField(Language, related_name="jobs")
    office_address = models.CharField(max_length=128)
    lunch_break = models.CharField(max_length=16, choices=LunchBreakEnum.choices())
    annual_salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    annual_salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    annual_salary_currency = models.ForeignKey(
        "core.Currency", 
        on_delete=models.SET_NULL, 
        related_name="jobs_with_salary_currency",
        null=True
    )
    annual_bonus_min = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    annual_bonus_max = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    annual_bonus_currency = models.ForeignKey(
        "core.Currency", 
        on_delete=models.SET_NULL, 
        related_name="jobs_with_bonus_currency",
        null=True,
    )
    recruiter = models.ForeignKey(
        "accounts.BusinessUser", 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="recruiting_jobs"
    )
    benefits = models.TextField(null=True)
    share_compensation = models.BooleanField(default=True)
    is_draft = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)
    additional_hours_min = models.IntegerField(default=0)
    additional_hours_max = models.IntegerField(default=0)
    additional_hours_description = models.TextField(null=True)
    technological_requirement = models.CharField(max_length=16, null=True)
    availability_timezone = TimeZoneField(default="America/Vancouver")

    department = models.ForeignKey("accounts.Department", null=True, on_delete=models.SET_NULL)
    role = models.ForeignKey("accounts.Role", null=True, on_delete=models.SET_NULL)
    skills = models.ManyToManyField("accounts.Skill")

    objects = JobManager()

    def __str__(self) -> str:
        return f"{self.title}({self.uid})"

    def business_logo(self):
        return self.created_by.business.get_logo()

    def business_name(self):
        return self.created_by.business.name


class JobPost(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    is_posted = models.BooleanField(default=False)
    country = models.ForeignKey("accounts.Country", on_delete=models.SET_NULL, null=True)
    province = models.CharField(max_length=64, null=True)
    postal_code = models.CharField(max_length=8, null=True)
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
    location_type = models.CharField(max_length=32, null=True)
    recruiter = models.ForeignKey(
        "accounts.BusinessUser", 
        null=True, 
        on_delete=models.SET_NULL, 
        related_name="recruiting_job_posts"
    )

    def __str__(self) -> str:
        return f"{self.job}({self.country})"


class JobApplication(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.SET_NULL, null=True)
    applicant = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE)
    is_available = models.BooleanField()
    accept_privacy = models.BooleanField(default=True)
    stage = models.CharField(max_length=16, choices=StageType.choices(), null=True, default=None)
    match = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.job_post} ({self.applicant})"


class SavedJob(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, null=True)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, null=True)

    def __str__(self) -> str:
        return f"{self.job_post} ({self.user})"


class JobDraft(BaseModel):
    user = models.OneToOneField("accounts.BusinessUser", on_delete=models.DO_NOTHING)
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


class QuestionOption(BaseModel):
    question = models.ForeignKey(ScreeningQuestion, on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False)
    text = models.CharField(max_length=128, null=True)


class Answer(BaseModel):
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE)
    text = models.TextField(null=True)


class RequiredAttribute(BaseModel):
    job = models.OneToOneField(Job, on_delete=models.CASCADE)
    skills = models.ManyToManyField("accounts.Skill")
    role = models.BooleanField(default=False)
    job_level = models.BooleanField(default=False)
    years_of_experience = models.BooleanField(default=False)
    business_model = models.ManyToManyField("BusinessModel")
    minimum_education_level = models.BooleanField(default=False)
    work_structure = models.BooleanField(default=False)
    technological_requirement = models.BooleanField(default=False)
    first_language = models.BooleanField(default=False)
    secondary_language = models.BooleanField(default=False)
    working_hours = models.BooleanField(default=False)
    location = models.BooleanField(default=False)
    years_of_experience = models.BooleanField(default=False)

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
        if self.business_model.count() > 0:
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




class OtherSkill(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)


class JobApplicationWithdrawal(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.SET_NULL, null=True, default=None)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.DO_NOTHING)
    feedback = models.TextField()



class JobInterview(BaseModel):
    application = models.ForeignKey("jobs.JobApplication", models.CASCADE)


class BusinessModel(BaseModel):
    name = models.CharField(max_length=64)
    description = models.TextField()

    def __str__(self) -> str:
        return self.name
