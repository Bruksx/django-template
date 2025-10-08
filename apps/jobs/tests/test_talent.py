import uuid
from datetime import timezone, time
from decimal import Decimal, ROUND_HALF_UP

from django.test import TestCase
from django.db import models
from ninja.testing import TestClient

from accounts.enums import BusinessUserRoleType, Days
from accounts.models import (
    Country, Industry, User, Talent, BusinessUser, Business, Role, EducationLevel, Department, BusinessIndustry,
    Skill, TalentAvailableDay, Experience, Education
)
from jobs.queries import add_job_post_annotations
from core.models import Currency, Language
from factories import (
    TalentFactory, JobPostFactory, BusinessUserFactory, JobFactory, WorkflowStageFactory,
    JobApplicationFactory, CountryFactory, ScreeningQuestionFactory, fake, RequiredAttributeFactory,
    EducationFactory, ExperienceFactory
)
from jobs.enums import WorkStructureEnum, LunchBreakEnum, PhaseType, JobStatusType, WithdrawalFeedbackType, \
    QuestionTypeEnum
from jobs.models import (
    JobPost, JobLevel, EmploymentType, SavedJob, JobApplication, RequiredAttribute, BusinessModel, AvailableDay,
    Job, RequiredSecondaryLanguage, RequiredSkill, JobInvite
)
from jobs.views import router

from core.models import State


class TalentJobListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.first()
        self.province = State.objects.first()
        self.industry = Industry.objects.first()
        self.business_industry = BusinessIndustry.objects.first()
        self.user_data = dict(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            password="securepassword",
        )
        self.user = User.objects.create_user(**self.user_data,
                                             email_verified=True,
                                             is_active=True)
        self.role = Role.objects.first()
        self.talent: Talent = TalentFactory.create(user=self.user, country=self.country, role=self.role)
        self.education_level = EducationLevel.objects.first()
        self.department = Department.objects.first()
        self.currency = Currency.objects.first()
        self.job_level = JobLevel.objects.first()
        self.employment_type = EmploymentType.objects.first()
        Experience.objects.filter(talent=self.talent).update(role=self.role, level=self.job_level)
        Education.objects.filter(talent=self.talent).update(level=self.education_level)

        self.user2 = User.objects.create_user(
            email="testuser1@example.com",
            password="securedPassword1",
            first_name="Test1",
            last_name="User1",
            phone_number="9098866699"
        )
        self.business = Business.objects.create(
            created_by=self.user2,
            name="Example Business",
            size=50,
            description="A sample business description.",
            website="https://example.com",
            address="Lekki, Lagos, Nigeria",
            country=self.country,
            industry=self.business_industry,
        )
        self.business_user = BusinessUser.objects.create(
            user=self.user,
            business=self.business,
            role=BusinessUserRoleType.OWNER.value
        )

        job = JobFactory.create(
            created_by=self.business_user,
            job_level=self.job_level,
            employment_type=self.employment_type,
            hiring_company_name="Example Company",
            title="Software Engineer",
            about="We are looking for a passionate...",  # Truncated for brevity
            years_of_experience=3,
            lunch_break=LunchBreakEnum.PAID.value,  # Assuming LunchBreakEnum has a PAID option
            minimum_education_level=self.education_level,
            role=self.role,
            department=self.department,
            availability_timezone=timezone.utc  # Set to UTC for this example
        )
        job.requiredattribute.update(
            role=True,
            job_level=True,
            years_of_experience=True,
            minimum_education_level=True,
            work_structure=True,
            technological_requirement=True,
            first_language=True,
            secondary_language=True,
            working_hours=True,
            location=True
        )
        self.job_post: JobPost = JobPostFactory.create(
            job=job,
            status=JobStatusType.POSTED.value,  # Can be changed to True for posting
            country=self.country,
            province=self.province,
            postal_code="M5V 1T6",  # Replace with actual postal code
            annual_salary_min=Decimal('80000.00'),  # Use Decimal for money fields
            annual_salary_max=Decimal('100000.00'),
            annual_salary_currency=self.currency,
            recruiter=self.business_user
        )

    def test_job_recommendations_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/job-recommendations", headers=headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get("talent/job-recommendations?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_saved_job_endpoints(self):
        SavedJob.objects.create(
            job_post=self.job_post,
            talent=self.talent
        )
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/saved-jobs", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        response = self.client.get("talent/saved-jobs?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_applied_job_endpoints(self):
        stage = WorkflowStageFactory.create(phase=PhaseType.INTERVIEW.value)
        application = JobApplication.objects.create(
            job_post=self.job_post,
            applicant=self.talent,
            stage=stage
        )
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/applied-jobs", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["application_uid"], str(application.uid))
        self.assertEqual(response.json()["results"][0]["stage"]["uid"], str(stage.uid))

        response = self.client.get("talent/applied-jobs?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)


    def test_job_post_list_endpoints(self):

        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/job-posts?sort_by=date-posted&page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertIn("match_score", response.json()["results"][0])
        match_score = response.json()["results"][0]["match_score"]
        self.assertGreaterEqual(match_score, 0)

        response = self.client.get("talent/job-posts?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get("talent/job-posts?search=test&page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)


class JobMatchTests(TestCase):
    def setUp(self):
        self.talent: Talent = TalentFactory.create()
        self.location = Country.objects.all()[0]
        self.location2 = Country.objects.all()[1]
        self.job: Job = JobFactory.create()
        self.job_post: JobPost = JobPostFactory.create(
            job=self.job,
        )
        self.required_attributes: RequiredAttribute = self.job.requiredattribute
        self.additional_languages = Language.objects.all()[:3]
        self.additional_languages2 = self.additional_languages[:1]
        self.role = Role.objects.order_by("pk")[0]
        self.role2 = Role.objects.order_by("pk")[1]

        self.tool_platform_skills = Skill.objects.filter(category__name="Tools/Platforms")[:3]
        self.methodology_skills = Skill.objects.filter(category__name="Common Methodologies/Frameworks")[:3]
        self.general_skills = Skill.objects.filter(category__name="General Skills")[:3]

        self.level1 = JobLevel.objects.all()[0]
        self.level2 = JobLevel.objects.all()[1]

    def test_location(self):
        self.talent.country = self.location
        self.job_post.country = self.location
        self.update_required_attributes(location=True)
        self.talent.save()
        self.job_post.save()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)

        job_post = queryset.first()
        location_score = Decimal(job_post.location_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        #test matching job location
        self.assertEqual(location_score, Decimal("6.67"))

        self.talent.country = self.location2

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)

        job_post = queryset.first()
        location_score = Decimal(job_post.location_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        #test non matching location
        self.assertEqual(location_score, Decimal("0.0"))

    def test_additional_language(self):
        self.job.additional_languages.add(*self.additional_languages)
        self.talent.additional_languages.add(*self.additional_languages2)
        self.update_required_attributes(location=True)
        self.talent.save()
        self.job_post.save()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()

        additional_language_score = Decimal(job_post.additional_language_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(additional_language_score, Decimal("2.22"))

        #add compulsory language
        RequiredSecondaryLanguage.objects.create(
            required_attribute=self.required_attributes,
            language=self.additional_languages[2]
        )

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()

        computed_match_score = Decimal(job_post.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(computed_match_score, Decimal("0.0"))
    
    def test_role(self):
        self.update_required_attributes(role=False)
        self.job.role = self.role
        experience: Experience = ExperienceFactory.create(
            talent=self.talent,
            role=self.role2
        )
        self.talent.role = self.role2
        self.talent.save()
        self.job.save()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()

        role_score = Decimal(job_post.role_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(role_score, Decimal("0.0"))

        self.update_required_attributes(role=True)
        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()

        computed_match_score = Decimal(job_post.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(computed_match_score, Decimal("0.0"))

        experience.role =self.job.role
        experience.save()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()

        role_score = Decimal(job_post.role_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(role_score, Decimal("6.67"))
    
    def test_skills(self):
        self.update_required_attributes()
        self.job.skills.add(*self.tool_platform_skills[:0], *self.general_skills[:0], *self.methodology_skills[:0])
        self.talent.skills.all().delete()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()

        tool_platform_score = Decimal(job_post.tools_platform_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        methodologies_score = Decimal(job_post.methodologies_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        general_skill_score = Decimal(job_post.general_skill_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(tool_platform_score, Decimal("6.67"))
        self.assertEqual(methodologies_score, Decimal("6.67"))
        self.assertEqual(general_skill_score, Decimal("6.67"))

    def test_missing_required_skill_returns_zero_score(self):
        self.update_required_attributes()
        self.job.skills.add(*self.tool_platform_skills, *self.general_skills, *self.methodology_skills)
        RequiredSkill.objects.create(
            skill=self.job.skills.first(),
            required_attribute=self.required_attributes,
        )
        self.talent.skills.all().delete()
        #self.talent.skills.add(*self.tool_platform_skills[:1], *self.general_skills[:2], *self.methodology_skills)
        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()

        #tool_platform_score = Decimal(job_post.tools_platform_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        #methodologies_score = Decimal(job_post.methodologies_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        #general_skill_score = Decimal(job_post.general_skill_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        computed_match_score = Decimal(job_post.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        #self.assertEqual(tool_platform_score, Decimal("0.00"))
        #self.assertEqual(methodologies_score, Decimal("0.00"))
        #self.assertEqual(general_skill_score, Decimal("0.00"))
        self.assertEqual(computed_match_score, Decimal("0.00"))

    def test_job_level_no_score(self):
        self.update_required_attributes()
        Experience.objects.filter(talent=self.talent).delete()
        
        ExperienceFactory.create(talent=self.talent, level=self.level1)
        self.job.job_level = self.level2
        self.job.save()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        job_level_score = Decimal(job_post.job_level_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(job_level_score, Decimal("0.0"))
    
    def test_job_level_full_score(self):
        self.update_required_attributes()
        Experience.objects.filter(talent=self.talent).delete()
        level1 = JobLevel.objects.all()[0]
        ExperienceFactory.create(talent=self.talent, level=level1)
        self.job.job_level = level1
        self.job.save()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        job_level_score = Decimal(job_post.job_level_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(job_level_score, Decimal("6.67"))
    
    def test_job_level_required_or_no_score(self):
        self.update_required_attributes(job_level=True)
        Experience.objects.filter(talent=self.talent).delete()
        level1 = JobLevel.objects.all()[0]
        level2 = JobLevel.objects.all()[1]
        ExperienceFactory.create(talent=self.talent, level=level1)
        self.job.job_level = level2
        self.job.save()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        computed_match_score = Decimal(job_post.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(computed_match_score, Decimal("0.0")) 

    def test_experience_score_full(self):
        self.update_required_attributes()
        self.talent.years_of_experience = 6
        self.job.years_of_experience = 5
        self.talent.save()
        self.job.save() 

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        experience_score = Decimal(job_post.experience_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(experience_score, Decimal("6.67"))
    
    def test_experience_score_zero(self):
        self.update_required_attributes()
        self.talent.years_of_experience = 6
        self.job.years_of_experience = 8
        self.talent.save()
        self.job.save() 

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        experience_score = Decimal(job_post.experience_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(experience_score, Decimal("0.0"))

    def test_working_hours_complete_match_full_score(self):
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        final_work_schedule_score = Decimal(job_post.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_working_hours_incomplete_match_partial_score(self):
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
            AvailableDay(
                job=self.job_post.job,
                day=Days.TUESDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        final_work_schedule_score = Decimal(job_post.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("3.33"))
    
    def test_working_hours_no_job_hours_full_score(self):
        available_days = []
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        final_work_schedule_score = Decimal(job_post.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_working_hours_flexible_talent_full_score(self):
        self.talent.flexible_availability = True
        self.talent.save()
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
            AvailableDay(
                job=self.job_post.job,
                day=Days.TUESDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        talent_available_days = []
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        final_work_schedule_score = Decimal(job_post.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_working_hours_flexible_job_full_score(self):
        self.talent.flexible_availability = True
        self.job.flexible_availability = True
        self.talent.save()
        available_days = []
        talent_available_days = []
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        final_work_schedule_score = Decimal(job_post.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_working_hours_required_incomplete_match_zero_computed_score(self):
        self.update_required_attributes(working_hours=True)
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
            AvailableDay(
                job=self.job_post.job,
                day=Days.TUESDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        computed_match_score = Decimal(job_post.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(computed_match_score, Decimal("0.00"))
    
    def test_working_hours_match_accross_timezones(self):
        self.job.availability_timezone = "America/Los_Angeles"
        self.talent.availability_timezone = "America/New_York" #3hrs ahead
        self.talent.save()
        self.job.save()
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(10, 0)
            ),
        ]
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(11, 0),
                end_time=time(13, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        final_work_schedule_score = Decimal(job_post.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_business_models_full_score(self):
        business_models = BusinessModel.objects.all()[:5]
        business_models2 = business_models[:2]
        self.job.business_models.add(*business_models)
        self.talent.business_models.add(*business_models2)
        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        business_model_score = Decimal(job_post.business_model_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(business_model_score, Decimal("2.67"))
    
    def test_missing_required_business_models_no_score(self):
        business_models = BusinessModel.objects.all()[:5]
        business_models2 = business_models[:2]
        self.job.business_models.add(*business_models)
        self.talent.business_models.add(*business_models2)
        self.required_attributes.business_models.add(*business_models[:5])
        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_job_post_annotations(queryset, self.talent)
        job_post = queryset.first()
        computed_match_score = Decimal(job_post.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(computed_match_score, Decimal("0.00"))
    
    def update_required_attributes(self, *args, **kwargs):
        for field_name in self.job.required_attributes_keys:
            if hasattr(self.required_attributes, field_name):
                field = getattr(self.required_attributes, field_name)
                if isinstance(field, models.BooleanField):
                    setattr(self.required_attributes, field, False)
        for field_name in kwargs:
            setattr(self.required_attributes, field_name, kwargs[field_name])
        self.required_attributes.save()



class ApplyToJobPostTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email="testuser1@example.com",
                                             password="securedPassword1",
                                             first_name="Test1",
                                             last_name="User1",
                                             phone_number="9098866699")
        self.country = Country.objects.first()
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.business_user = self.job.created_by
        self.job_post = JobPostFactory.create(
            status=JobStatusType.POSTED.value,
            job=self.job,)
        self.test_data = {
            "available_for_schedule": True
        }
        self.url = lambda job_post_uid: f"talent/job-posts/{job_post_uid}/apply"
        WorkflowStageFactory.create(phase=PhaseType.REJECTED.value, created_by=self.job.created_by)

    def test_apply_to_job_post_without_screening_answers(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 0)
        response = self.client.post(self.url(self.job_post.uid), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)

        # test to ensure that you cannot apply for one job twice
        response = self.client.post(self.url(self.job_post.uid), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_apply_to_job_post_with_screening_answers(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        questions = ScreeningQuestionFactory.create_batch(5, job=self.job)
        data = list()
        for question in questions:
            answer_dict = dict(question=question.uid)
            if question.type == QuestionTypeEnum.SINGLE_SELECT.value:
                answer_dict["options"] = [question.questionoption_set.first().uid]
            elif question.type == QuestionTypeEnum.MULTI_SELECT.value:
                answer_dict["options"] = [option.uid for option in question.questionoption_set.all()[:2]]
            elif question.type == QuestionTypeEnum.TEXT.value:
                answer_dict["text"] = fake.text(max_nb_chars=20)
            elif question.type == QuestionTypeEnum.FILE.value:
                answer_dict["files"] = ["http://test.com"]
            data.append(answer_dict)
        self.test_data["answers"] = data
        response = self.client.post(self.url(self.job_post.uid),
                                    headers=headers, json=self.test_data)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        application = self.talent.jobapplication_set.first()
        self.assertEqual(application.answer_set.count(), 5)

    def test_by_business_user(self):

        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.job_post.uid), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_with_invalid_job_post_uid(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.post(self.url(uuid.uuid4()), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 404)


    def test_low_application_score(self):
        match_score = self.talent.job_match_score(self.job_post)
        self.job.update(min_match_score=(match_score + 1))
        self.job.refresh_from_db()
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 0)
        response = self.client.post(self.url(self.job_post.uid), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        application = self.talent.jobapplication_set.first()
        self.assertEqual(application.stage.phase, PhaseType.REJECTED.value)



class WithdrawJobApplicationTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email="testuser1@example.com",
                                             password="securedPassword1",
                                             first_name="Test1",
                                             last_name="User1",
                                             phone_number="9098866699")
        self.country = Country.objects.first()
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.job_post = JobPostFactory.create(
            job=self.job,
            status=JobStatusType.POSTED.value
        )
        self.stage = WorkflowStageFactory.create(phase=PhaseType.NEW.value)
        self.job_application = JobApplicationFactory.create(
            job_post=self.job_post,
            stage=self.stage,
            applicant=self.talent
        )

    def test_withdraw_job_application(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        job_application_id = str(JobApplication.objects.first().uid)
        data = {
            "feedback_type": WithdrawalFeedbackType.SKILLS.value,
            "feedback": "Test Feedback"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        response = self.client.post(f"talent/job-posts/applications/{job_application_id}/withdraw",
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 0)

    def test_withdraw_for_job_application_with_stage(self):
        stage = WorkflowStageFactory.create(phase=PhaseType.REJECTED.value)
        self.job_application.stage = stage
        self.job_application.save()
        self.job_application.refresh_from_db()
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        job_application_id = str(JobApplication.objects.first().uid)
        data = {
            "feedback_type": WithdrawalFeedbackType.SKILLS.value,
            "feedback": "Test Feedback"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        response = self.client.post(f"talent/job-posts/applications/{job_application_id}/withdraw",
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 400)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)


class ShareJobPostViaEmailTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email="testuser1@example.com",
                                             password="securedPassword1",
                                             first_name="Test1",
                                             last_name="User1",
                                             phone_number="9098866699")
        self.user2 = User.objects.create_user(email="testuser2@example.com",
                                             password="securedPassword1",
                                             first_name="Test2",
                                             last_name="User2",
                                             phone_number="9098866699")
        self.talent2 = Talent.objects.create(user=self.user2)

        self.country = Country.objects.first()
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.job_post = JobPostFactory.create(
            job=self.job,)

        self.url = f"share/via-email"

    def test_share_job_post_via_email(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
         "emails": [self.talent.user.email, "testuser4@example.com"],
         "jobs": [str(self.job.uid)]
        }
        response = self.client.post(self.url,
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 200)

class InviteToApplyTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.user = User.objects.create_user(email="testuser2@example.com",
                                             password="securedPassword1",
                                             first_name="Test2",
                                             last_name="User2",
                                             phone_number="9098866699")
        self.talent = Talent.objects.create(user=self.user)

        self.country = Country.objects.first()
        self.job = JobFactory.create(
            title="Test Job", created_by=self.business_user
        )
        self.job_post = JobPostFactory.create(
            job=self.job,)

        self.url = "talent/invite-to-apply"

    def test_invite_to_apply(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        count = self.business_user.business.total_invitations_sent()

        response = self.client.post(
            self.url, headers=headers,
            json=dict(
                jobs=[str(self.job.uid)],
                talents=[str(self.talent.uid)]
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobInvite.objects.count(), 1)
        self.assertEqual(self.business_user.business.total_invitations_sent(), count + 1)


class SaveJobTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email="testuser1@example.com",
                                             password="securedPassword1",
                                             first_name="Test1",
                                             last_name="User1",
                                             phone_number="9098866699")
        self.country = Country.objects.first()
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.job_post = JobPostFactory.create(
            job=self.job,)

    def test_save_job(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertEqual(self.talent.saved_jobs().count(), 0)
        job_post_id = str(JobPost.objects.first().uid)
        response = self.client.post(f"talent/job-posts/{job_post_id}/save",
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.saved_jobs().count(), 1)
        # test to ensure that you cannot save for one job twice
        response = self.client.post(f"talent/job-posts/{job_post_id}/save",
                                    headers=headers)
        self.assertEqual(response.status_code, 400)

class DiscardSavedJobTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email="testuser1@example.com",
                                             password="securedPassword1",
                                             first_name="Test1",
                                             last_name="User1",
                                             phone_number="9098866699")
        self.country = Country.objects.first()
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.job_post = JobPostFactory.create(
            job=self.job,)

    def test_discard_saved_job_endpoint_without_job_post_saved(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertEqual(self.talent.saved_jobs().count(), 0)
        job_post_id = str(JobPost.objects.first().uid)
        response = self.client.post(f"talent/job-posts/{job_post_id}/discard",
                                    headers=headers)
        self.assertEqual(response.status_code, 404)
        self.talent.refresh_from_db()

    def test_discard_saved_job_endpoint_with_job_post_saved(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        SavedJob.objects.create(
            job_post=self.job_post,
            talent=self.talent
        )
        self.assertEqual(self.talent.saved_jobs().count(), 1)
        job_post_id = str(JobPost.objects.first().uid)
        response = self.client.post(f"talent/job-posts/{job_post_id}/discard",
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.saved_jobs().count(), 0)

class TestShareJobViaChat(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.talent = TalentFactory.create()
        TalentFactory.create_batch(3, country=self.talent.country)
        self.job_post = JobPostFactory.create(country=self.talent.country)
        self.url = f"share/via-chat"

    def test_share_job_post_via_chat(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talents" : list(Talent.objects.only("uid").exclude(uid=self.talent.uid).values_list("uid", flat=True)),
            "jobs": [self.job_post.job.uid]
        }
        self.assertEqual(self.job_post.message_set.count(), 0)
        response = self.client.post(self.url, headers=header, json=data)
        self.job_post.refresh_from_db()
        self.assertEqual(self.job_post.message_set.count(), 3)
        message = self.job_post.message_set.first()
        self.assertEqual(message.job_post.job.id, self.job_post.job.id)
        self.assertEqual(response.status_code, 200)

    def test_request_by_business_user(self):
        business_user = BusinessUserFactory.create()
        header = {
            "Authorization": f"Bearer {business_user.user.token}"
        }
        data = {
            "talents" : list(Talent.objects.only("uid").exclude(uid=self.talent.uid).values_list("uid", flat=True)),
            "jobs": [self.job_post.job.uid]
        }
        response = self.client.post(self.url, headers=header, json=data)
        self.assertEqual(response.status_code, 200)


    def test_empty_talent_ids(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talents" : [],
            "jobs": [self.job_post.job.uid]
        }
        response = self.client.post(self.url, headers=header, json=data)
        self.assertEqual(response.status_code, 400)

    def test_wrong_talent_ids_data(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talents" : [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()],
            "jobs": [self.job_post.job.uid]
        }
        response = self.client.post(self.url, headers=header, json=data)
        self.assertEqual(response.status_code, 200)

class TestJobRecommendationsEndpoint(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = lambda talent_uid: f"talents/{talent_uid}/job-recommendations"
        self.business_user = BusinessUserFactory.create()
        self.business = self.business_user.business
        country = CountryFactory.create()
        years_of_experience = 3
        self.talent = TalentFactory.create(years_of_experience=years_of_experience, country=country)
        jobs = JobFactory.create_batch(5, created_by=self.business_user, years_of_experience=years_of_experience)
        for job in jobs:
            job.requiredattribute.update(job=job, years_of_experience=True, location=True)
            JobPostFactory.create(job=job, posted_by=self.business_user, country=country, status=JobStatusType.POSTED.value)
        JobApplicationFactory.create(job_post=JobPost.objects.first(), applicant=self.talent)

    def test_job_recommendations_endpoint(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.talent.uid), headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_endpoint_by_talent(self):
        headers = {
            "authorization": f"Bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url(self.talent.uid), headers=headers)
        self.assertEqual(response.status_code, 403)


    def test_endpoint_with_invalid_talent_uid(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid.uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)
