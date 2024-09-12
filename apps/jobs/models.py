from django.db import models
from core.models import BaseModel, Language
from accounts.models import User, Country, Business
from .enums import WorkStructureEnum, LunchBreakEnum, QuestionTypeEnum, StageType
from timezone_field import TimeZoneField


# Create your models here.
class EmploymentType(BaseModel):
    name = models.CharField(max_length=128)
    parent = models.ForeignKey("EmploymentType", on_delete=models.DO_NOTHING, null=True, blank=True)

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
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    job = models.ForeignKey("Job", on_delete=models.DO_NOTHING)
    day = models.CharField(max_length=32)
    end_time = models.TimeField(null=True)
    start_time = models.TimeField(null=True)


class Job(BaseModel):
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
    minimum_education_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.DO_NOTHING, null=True)
    business_models = models.ManyToManyField("BusinessModel")
    job_level = models.ForeignKey(JobLevel, on_delete=models.DO_NOTHING, null=True)
    qualification = models.ForeignKey(Qualification, on_delete=models.DO_NOTHING, null=True)
    work_structure = models.CharField(choices=WorkStructureEnum.choices())
    first_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    additional_languages = models.ManyToManyField(Language, related_name="jobs")
    office_address = models.CharField(max_length=128)
    lunch_break = models.CharField(max_length=16, choices=LunchBreakEnum.choices())
    annual_salary_min = models.DecimalField(max_digits=12, decimal_places=2)
    annual_salary_max = models.DecimalField(max_digits=12, decimal_places=2)
    annual_salary_currency = models.CharField(max_length=8)
    annual_bonus_min = models.DecimalField(max_digits=12, decimal_places=2)
    annual_bonus_max = models.DecimalField(max_digits=12, decimal_places=2)
    annual_bonus_currency = models.CharField(max_length=8)
    recruiter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="recruiting_jobs")
    benefits = models.TextField(null=True)
    share_compensation = models.BooleanField(default=True)
    is_draft = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)
    additional_hours_min = models.IntegerField(default=0)
    additional_hours_max = models.IntegerField(default=0)
    additional_hours_description = models.TextField(null=True)
    technological_requirement = models.CharField(max_length=16, null=True)
    avaibility_timezone = TimeZoneField(default="America/Vancouver")

    def __str__(self) -> str:
        return f"{self.title}({self.uid})"


class JobPost(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    is_posted = models.BooleanField(default=False)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    province = models.CharField(max_length=64, null=True)
    postal_code = models.CharField(max_length=8, null=True)
    annual_salary_min = models.DecimalField(max_digits=12, decimal_places=2)
    annual_salary_max = models.DecimalField(max_digits=12, decimal_places=2)
    annual_salary_currency = models.CharField(max_length=8)
    annual_bonus_min = models.DecimalField(max_digits=12, decimal_places=2)
    annual_bonus_max = models.DecimalField(max_digits=12, decimal_places=2)
    annual_bonus_currency = models.CharField(max_length=8)
    location_type = models.CharField(max_length=32, null=True)
    recruiter = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name="recruiting_job_posts")
    #location_type = models.CharField(max_length=32, null=True)

    def __str__(self) -> str:
        return self.country


class JobApplication(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE)
    is_available = models.BooleanField()
    accept_privacy = models.BooleanField(default=True)
    stage = models.CharField(max_length=16, choices=StageType.choices())
    match = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.job} ({self.applicant})"


class SavedJob(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, null=True)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.CASCADE, null=True)

    def __str__(self) -> str:
        return f"{self.job} ({self.user})"


class JobDraft(BaseModel):
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)


class JobFilter(BaseModel):
    talent = models.OneToOneField("accounts.Talent", on_delete=models.CASCADE, null=True)
    years_of_experience = models.PositiveSmallIntegerField(default=1)
    office_location = models.ForeignKey("accounts.Country", on_delete=models.SET_NULL, null=True)
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey("accounts.Department", on_delete=models.SET_NULL, null=True)
    minimum_education_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True)
    location_type = models.CharField(choices=WorkStructureEnum.choices(), default=WorkStructureEnum.IN_OFFICE)
    remove_applied_jobs = models.BooleanField(default=False)


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
    business_model = models.ManyToManyField("BusinessModel")
    minimum_education_level = models.BooleanField(default=False)
    work_structure = models.BooleanField(default=False)
    technological_requirement = models.BooleanField(default=False)
    first_language = models.BooleanField(default=False)
    secondary_language = models.BooleanField(default=False)
    working_hours = models.BooleanField(default=False)
    location = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.job}({self.uid})"


class OtherSkill(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)


class JobApplicationWithdrawal(BaseModel):
    job_post = models.ForeignKey(JobPost, on_delete=models.DO_NOTHING)
    talent = models.ForeignKey("accounts.Talent", on_delete=models.DO_NOTHING)
    feedback = models.TextField()


class BusinessModel(BaseModel):
    name = models.CharField(max_length=64)
    description = models.TextField()

    def __str__(self) -> str:
        return self.name