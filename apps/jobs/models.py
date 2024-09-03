from django.db import models
from core.models import BaseModel
from accounts.models import User, Country, Language, Business


# Create your models here.
class EmploymentType(BaseModel):
    name = models.CharField(max_length=128)
    parent = models.ForeignKey("EmploymentType", on_delete=models.DO_NOTHING, null=True)

    def __str__(self) -> str:
        return self.name


class EducationLevel(BaseModel):
    name = models.CharField(max_length=64)

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
    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    FLEXIBLE = "flexible"
    DAY_CHOICES = (
        (SUNDAY, SUNDAY),
        (MONDAY, MONDAY),
        (TUESDAY, TUESDAY),
        (WEDNESDAY, WEDNESDAY),
        (THURSDAY, THURSDAY),
        (FRIDAY, FRIDAY),
        (SATURDAY, SATURDAY),
        (FLEXIBLE, FLEXIBLE)
    )
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    job = models.ForeignKey("Job", on_delete=models.DO_NOTHING)
    day = models.CharField(max_length=32)
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)


class Job(BaseModel):
    REMOTE = "remote"
    HYBRID = "hybrid"
    IN_OFFICE = "in office"
    WORKSTRUCTURE_CHOICES = (
        (REMOTE, "Remote"),
        (HYBRID, "Hybrid"),
        (IN_OFFICE, "In-Office"),
    )
    WINDOWS = "windows"
    MACBOOK = "macbook"
    EITHER = "either"
    TECHNOLOGICAL_REQUIREMENT_CHOICES = (
        (WINDOWS, "Windows"),
        (MACBOOK, "Macbook"),
        (EITHER, "Either"),
    )
    PAID = "paid"
    UNPAID = "unpaid"
    LUNCH_BREAK_CHOICES = (
        (PAID, PAID),
        (UNPAID, UNPAID)
    )
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    business = models.ForeignKey(Business, on_delete=models.DO_NOTHING)
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.DO_NOTHING)
    hiring_company_name = models.CharField(max_length=64, null=True)
    hiring_company_description = models.TextField()
    title = models.CharField(max_length=32)
    about = models.TextField()
    years_of_experience = models.IntegerField()
    minimum_education_level = models.ForeignKey(EducationLevel, on_delete=models.DO_NOTHING, null=True)
    job_level = models.ForeignKey(JobLevel, on_delete=models.DO_NOTHING, null=True)
    qualification = models.ForeignKey(Qualification, on_delete=models.DO_NOTHING, null=True)
    work_structure = models.CharField(choices=WORKSTRUCTURE_CHOICES)
    first_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    additional_languages = models.ManyToManyField(Language, related_name="jobs")
    office_address = models.CharField(max_length=128)
    lunch_break = models.CharField(max_length=16)
    annual_salary_min = models.DecimalField(max_digits=12, decimal_places=2)
    annual_salary_max = models.DecimalField(max_digits=12, decimal_places=2)
    annaul_salary_curreny = models.CharField(max_length=8)
    annual_bonus_min = models.DecimalField(max_digits=12, decimal_places=2)
    annual_bonus_max = models.DecimalField(max_digits=12, decimal_places=2)
    annaul_bonus_curreny = models.CharField(max_length=8)
    recruiter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="recruiting_jobs")
    share_compensation = models.BooleanField(default=True)
    is_draft = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class JobPost(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    is_posted = models.BooleanField(default=False)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    annual_salary_min = models.DecimalField(max_digits=12, decimal_places=2)
    annual_salary_max = models.DecimalField(max_digits=12, decimal_places=2)
    annaul_salary_curreny = models.CharField(max_length=8)
    annual_bonus_min = models.DecimalField(max_digits=12, decimal_places=2)
    annual_bonus_max = models.DecimalField(max_digits=12, decimal_places=2)
    annaul_bonus_curreny = models.CharField(max_length=8)


    def __str__(self) -> str:
        return self.country


class JobApplication(BaseModel):
    SCREENING = "screening"
    INTERVIEW = "interview"
    INTERVIEW_2 = "interview 2"
    HIRED = "hired"
    ONBOARDING = "onboarding"
    REJECTED = "rejected"
    STAGE_CHOICES = (
        (SCREENING, SCREENING),
        (INTERVIEW, INTERVIEW),
        (INTERVIEW_2, INTERVIEW_2),
        (ONBOARDING, ONBOARDING),
        (HIRED, HIRED),
        (REJECTED, REJECTED),
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE)
    is_available = models.BooleanField()
    accept_privacy = models.BooleanField(default=True)
    stage = models.CharField(max_length=16, choices=STAGE_CHOICES)
    match = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.job} ({self.applicant})"


class SavedJob(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)

    def __str__(self) -> str:
        return f"{self.job} ({self.user})"


class SkillCategory(BaseModel):
    name = models.CharField(max_length=64)

    def __str__(self) -> str:
        return self.name


class Skill(BaseModel):
    category = models.ForeignKey(SkillCategory, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=64)

    def __str__(self) -> str:
        return self.name


class JobDraft(BaseModel):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)


class JobFilter(BaseModel):
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
