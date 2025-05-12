from typing import List

from django.db import models
from django.db.models import F, Q, QuerySet
from monkeypatches.q_cluster import async_task
from timezone_field import TimeZoneField

from accounts.enums import Days
from accounts.models import Talent, TalentAvailableDay
from core.models import BaseModel, Language
from jobs.managers import JobManager
from settings.enums import PlaceHolderType
from .enums import WorkStructureEnum, LunchBreakEnum, QuestionTypeEnum, PhaseType, WithdrawalFeedbackType, \
    JobStatusType


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
    created_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.SET_NULL, null=True) #TODO take care during delete account
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.SET_NULL, null=True)
    hiring_company_name = models.CharField(max_length=64, null=True)
    hiring_company_description = models.TextField(null=True)
    title = models.CharField(max_length=100, null=True)
    about = models.TextField(null=True)
    years_of_experience = models.IntegerField(null=True)
    minimum_education_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True)
    business_models = models.ManyToManyField("BusinessModel", blank=True)
    job_level = models.ForeignKey(JobLevel, on_delete=models.SET_NULL, null=True)
    qualification = models.TextField(null=True, blank=True)
    work_structure = models.CharField(choices=WorkStructureEnum.choices(), null=True, blank=True)
    first_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    additional_languages = models.ManyToManyField(Language, related_name="jobs")
    office_address = models.CharField(max_length=128)
    lunch_break = models.CharField(max_length=50, choices=LunchBreakEnum.choices())
    lunch_break_time = models.PositiveSmallIntegerField(default=0)
    responsibilities = models.JSONField(default=list, blank=True)
    additional_hours_description = models.TextField(null=True)
    additional_hours_start = models.TimeField(null=True)
    additional_hours_end = models.TimeField(null=True)
    technological_requirement = models.CharField(max_length=100, null=True, blank=True)
    availability_timezone = TimeZoneField(default="America/Vancouver")
    flexible_availability = models.BooleanField(default=False)
    department = models.ForeignKey("accounts.Department", null=True, on_delete=models.SET_NULL)
    role = models.ForeignKey("accounts.Role", null=True, on_delete=models.SET_NULL)
    skills = models.ManyToManyField("accounts.Skill")
    min_match_score = models.FloatField(null=True)

    objects = JobManager()

    required_attributes_keys = (
            "skills", "role", "job_level", "years_of_experience",
            "business_models", "minimum_education_level",
            "work_structure", "technological_requirement",
            "first_language", "secondary_language", "working_hours",
            "location"
        )

    def get_availability(self, schema, query=None):
        data = list()
        for value in Days.values():
            availability = query.filter(day=value).first()
            data.append({
                "day": value,
                "availability": schema.from_orm(availability) if availability else None
            })
        return data

    def send_alerts(self):
        async_task(JobAlert.send_alerts,self)
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
        return f"{self.title}({self.uid})"

    def logo_url(self):
        return self.logo.url if self.logo else self.created_by.business.get_logo()

    def hiring_company(self):
        if self.hiring_company_name:
            return self.hiring_company_name
        return self.created_by.business.name

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
    status = models.CharField(max_length=50, choices=JobStatusType.choices(), default=JobStatusType.DRAFT.value)
    date_posted = models.DateTimeField(null=True)
    country = models.ForeignKey("accounts.Country", on_delete=models.SET_NULL, null=True)
    province = models.CharField(max_length=64, null=True)
    postal_code = models.CharField(max_length=20, null=True)
    benefits = models.JSONField(default=list, blank=True)
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
        related_name="posted_by",
        blank=True
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
            talents = Talent.objects.select_related("user").filter(visible=True)
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

        if required_attribute.work_structure and job.work_structure:
            query = get_query(Q(work_model=job.work_structure))

        if required_attribute.first_language:
            query = get_query(Q(native_language=job.first_language))
        if required_attribute.secondary_language and job.additional_languages.count() > 0:
            ids = job.additional_languages.values_list("id", flat=True)
            query = get_query(Q(additional_languages__id__in=ids))
        if required_attribute.working_hours:
            query = get_query(Q(talentavailableday__id__in=TalentAvailableDay.objects.filter(job.availability_query()).only("id").values_list("id", flat=True)))
        if required_attribute.location:
            query = get_query(Q(country=self.country))
        talents =Talent.objects.select_related("user").filter(visible=True)
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
            if weak is False:
                data["match_score"] = 100
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
                fits = talent.work_model == job.work_structure
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
        match_score = int((score/total_score) * 100)
        if weak is False:
            data["match_score"] = match_score
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
        return self.strength(talent).get("match_score", 0)





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

    def other_application(self):
        return JobApplication.objects.filter(job_post=self.job_post, applicant=self.applicant).exclude(id=self.id).last()


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
        if not ScreeningQuestion.objects.filter(job=self.job_post.job, is_knockout=True).exists():
            return False
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
    job_role = models.ForeignKey("accounts.Role", on_delete=models.SET_NULL, null=True)
    years_of_experience = models.CharField(max_length=128, null=True)
    office_location = models.ForeignKey("accounts.Country", on_delete=models.SET_NULL, null=True)
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.SET_NULL, null=True)
    minimum_education_level = models.ForeignKey("accounts.EducationLevel", on_delete=models.SET_NULL, null=True)
    job_level = models.ForeignKey(JobLevel, on_delete=models.SET_NULL, null=True)
    company = models.ForeignKey("accounts.Business", on_delete=models.SET_NULL, null=True)
    location_type = models.CharField(choices=WorkStructureEnum.choices(), default=None, null=True)
    remove_applied_jobs = models.BooleanField(default=False)

    def get_queryset(self, queryset=None, filters=None, extra_sorts:List[str]=None)->QuerySet:
        """
         get job post queryset based on this filter

         Args:
             queryset: Job post queryset
             filters: JobPostFilterSchema instance from API query params
             extra_sorts: extra sort fields based on model fields

        Returns:
            Job post queryset
        """
        from jobs.services import order_job_posts
        if not queryset:
            queryset = JobPost.objects.all()
        country = self.office_location if self.office_location else self.talent.country
        if country:
            queryset = queryset.filter(country=country)
        if filters and filters.search:
            queryset = queryset.filter(job__title__icontains=filters.search)
        if self.company:
            queryset = queryset.filter(job__created_by__business=self.company)
        if self.job_role:
            queryset = queryset.filter(job__role=self.job_role)
        if self.location_type:
            queryset = queryset.filter(job__work_structure=self.location_type)
        print("queryset: ", queryset)

        if self.employment_type:
            queryset = queryset.filter(job__employment_type=self.employment_type)
        if self.job_level:
            queryset = queryset.filter(job__job_level=self.job_level)
        if self.minimum_education_level:
            queryset = queryset.filter(job__minimum_education_level=self.minimum_education_level)
        if self.years_of_experience:
            if self.years_of_experience == "0 years":
                queryset = queryset.filter(Q(job__years_of_experience__isnull=True)|Q(job__years_of_experience=0))
            elif self.years_of_experience == "20+ years":
                queryset = queryset.filter(job__years_of_experience__gte=20)
            elif "-" in self.years_of_experience:
                years = map(int, self.years_of_experience.replace(" years", "").split("-"))
                queryset = queryset.filter(job__years_of_experience__range=years)
        sorts = []
        if not extra_sorts:
            extra_sorts = []
        if filters and filters.sort_by:
            sorts = filters.sort_by.split(",")
        return order_job_posts(queryset, sorts, *extra_sorts)

    def results(self):
        return self.get_queryset().count()


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

    @staticmethod
    def format_skills_under_category(skills):
        from jobs.schemas import SkillSchema, JobSkillSchema
        from accounts.models import SkillCategory
        categories = SkillCategory.objects.only("id", "name")
        data = list()
        for category in categories:
            data.append(JobSkillSchema(
                category=category.name,
                skills=[SkillSchema.from_orm(skill) for skill in skills.filter(category_id=category.id)]
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
        user_ids = (cls.objects.filter(
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


