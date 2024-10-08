import logging
from datetime import date, timezone, datetime
from decimal import Decimal
from xmlrpc.client import DateTime

from django.test import TestCase

from accounts.enums import BusinessUserRoleType, Days
from accounts.models import User, Talent, SkillCategory, Skill, Department, Experience, Role, Education, EducationLevel, \
    BusinessUser, Business, Country, TalentAvailableDay
from accounts.schemas.talent import TalentSkillSchema, MonthlyChartSchema, TalentAvailableDaySchema
from chats.models import Conversation, Message
from core.models import Currency
from jobs.enums import LunchBreakEnum, WorkStructureEnum, StageType
from jobs.models import JobLevel, EmploymentType, Job, JobPost, RequiredAttribute, BusinessModel, AvailableDay, \
    JobApplication, JobInterview, SavedJob


class TalentModelTest(TestCase):
    def setUp(self):
        BusinessModel.objects.bulk_create(
            [BusinessModel(
                name=data['name'],
                description=data['description']
            )
            for data in [
                dict(name="Fintech", description=""),
                dict(name="Youth", description=""),
                dict(name="Kiln", description="")
            ]
            ]
        )
        self.department = Department.objects.first()
        self.role = Role.objects.first()
        self.currency = Currency.objects.first()
        self.job_level = JobLevel.objects.first()
        self.employment_type = EmploymentType.objects.first()
        self.education_level = EducationLevel.objects.first()
        self.country = Country.objects.first()
        self.user2 = User.objects.create_user(
            email="testuser1@example.com",
            password="securedPassword1",
            first_name="Test1",
            last_name="User1",
            phone_number="9098866699"
        )
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="securedPassword",
            first_name="Test",
            last_name="User",
            phone_number="909889999"
        )
        self.talent = Talent.objects.create(
            user=self.user
        )
        self.business = Business.objects.create(
            created_by=self.user2,
            name="Example Business",
            size=50,
            description="A sample business description.",
            website="https://example.com",
            location="Lekki, Lagos, Nigeria",
            industry="Technology"
        )
        self.business_user = BusinessUser.objects.create(
            user=self.user,
            business=self.business,
            role=BusinessUserRoleType.OWNER.value

        )
        self.talent.skills.set(Skill.objects.all()[:3])
        Experience.objects.create(
            talent=self.talent,
            role=self.role,
            company="TestCompany",
            annual_salary = 700,
            annual_salary_currency=self.currency,
            annual_salary_bonus=700,
            annual_salary_bonus_currency=self.currency,
            level=self.job_level,
            employment_type=self.employment_type,
            start_date=date(year=2022, month=1, day=1),
            end_date=date(year=2024, month=1, day=1),
            currently_works_here=False
        )
        Education.objects.create(
            talent=self.talent,
            level = self.education_level,
            start_date=date(year=2001, month=1, day=6),
            end_date=date(year=2005, month=9, day=8),
            major="Science",
            university="University of Lagos"
        )
        job = Job.objects.create(
            created_by=self.business_user,
            job_level=self.job_level,
            employment_type=self.employment_type,
            hiring_company_name="Example Company",
            title="Software Engineer",
            about="We are looking for a passionate...",  # Truncated for brevity
            years_of_experience=3,
            lunch_break=LunchBreakEnum.PAID.value,  # Assuming LunchBreakEnum has a PAID option
            annual_salary_min=100000.00,
            annual_salary_max=120000.00,
            annual_salary_currency=self.currency,
            availability_timezone=timezone.utc  # Set to UTC for this example
        )
        self.job_post = JobPost.objects.create(
            job=job,
            is_posted=False,  # Can be changed to True for posting
            country=self.country,
            province="Ontario",
            postal_code="M5V 1T6",  # Replace with actual postal code
            annual_salary_min=Decimal('80000.00'),  # Use Decimal for money fields
            annual_salary_max=Decimal('100000.00'),
            annual_salary_currency=self.currency,
            location_type=WorkStructureEnum.HYBRID.value,
            recruiter=self.business_user
        )
        self.job_required_attrs = RequiredAttribute.objects.create(
            job=job,
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
        self.job_required_attrs.skills.set(Skill.objects.all()[:2])
        self.job_required_attrs.business_model.set(BusinessModel.objects.all()[:2])
        self.job_required_attrs.refresh_from_db()
        TalentAvailableDay.objects.create(
            talent=self.talent,
            day=Days.WEDNESDAY.value,
            start_time=datetime.strptime("10:00:00", "%H:%M:%S").time(),  # "10:00:00",
            end_time=datetime.strptime("16:00:00", "%H:%M:%S").time()  # "16:00:00"
        )
        TalentAvailableDay.objects.create(
            talent=self.talent,
            day=Days.MONDAY.value,
            start_time=datetime.strptime("10:00:00", "%H:%M:%S").time(),  # "10:00:00",
            end_time=datetime.strptime("16:00:00", "%H:%M:%S").time()  # "16:00:00"
        )

        AvailableDay.objects.create(
            job=job,
            day=Days.MONDAY.value,
            start_time=datetime.strptime("10:00:00", "%H:%M:%S").time(),  # "10:00:00",
            end_time=datetime.strptime("16:00:00", "%H:%M:%S").time()  # )"16:00:00"
        )

        application = JobApplication.objects.create(
            job_post=self.job_post,
            applicant = self.talent,
        is_available = True,
        accept_privacy = True,
        stage = StageType.INTERVIEW.value,
        match = 5
        )
        JobInterview.objects.create(
            application=application
        )
        conversation = Conversation.objects.create()
        conversation.users.set([self.user2, self.user])
        conversation.refresh_from_db()
        Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            job_post=self.job_post,
            body="Hello"

        )

    def test_get_skills(self):
        skills = self.talent.get_skills()
        self.assertTrue(isinstance(skills, list))
        self.assertTrue(isinstance(skills[0],TalentSkillSchema))

    def test_experience_history(self):
        experience = self.talent.experience_history()
        self.assertEqual(experience.count(), 1)

    def test_years_of_experience(self):
        Experience.objects.create(
            talent=self.talent,
            role=self.role,
            company="TestCompanyII",
            annual_salary=700,
            annual_salary_currency=self.currency,
            annual_salary_bonus=700,
            annual_salary_bonus_currency=self.currency,
            level=self.job_level,
            employment_type=self.employment_type,
            start_date=date(year=2020, month=1, day=1),
            end_date=date(year=2023, month=1, day=1),
            currently_works_here=False
        )
        years_of_experience = self.talent.years_of_experience()
        self.assertTrue(isinstance(years_of_experience, int))
        self.assertEqual(years_of_experience, 4)

    def test_education_history(self):
        education = self.talent.education_history()
        self.assertEqual(education.count(), 1)


    def test_job_post_matches(self):
        job_post_matches = self.talent.job_post_matches()
        self.assertEqual(job_post_matches.count(), 1)

    def test_job_match_score(self):
        match_score = self.talent.job_match_score(self.job_post)
        self.assertEqual(match_score, 54)
        self.talent.business_models.set(BusinessModel.objects.all()[:3])
        self.talent.refresh_from_db()
        self.job_required_attrs.secondary_language = False
        self.job_required_attrs.save()
        self.job_required_attrs.refresh_from_db()
        match_score = self.talent.job_match_score(self.job_post)
        self.assertEqual(match_score, 70)

    def test_job_applications(self):
        applications = self.talent.job_applications()
        self.assertEqual(applications.count(), 1)
        start_date = date(year=2020, month=1, day=1)
        end_date = date(year=2023, month=1, day=1)
        applications = self.talent.job_applications(start_date=start_date, end_date=end_date)
        self.assertEqual(applications.count(), 0)




    def test_invitations_to_apply(self):
        invitations =  self.talent.invitations_to_apply()
        self.assertEqual(invitations, 1)

    def test_job_interviews(self):
        interviews = self.talent.job_interviews()
        self.assertEqual(interviews.count(), 1)

    def test_applications_made_chart(self):
        applications_chart = self.talent.applications_made_chart()
        self.assertTrue(isinstance(applications_chart, list))
        self.assertTrue(isinstance(applications_chart[0], MonthlyChartSchema))
        self.assertEqual(len(applications_chart), 12)


    def test_interviews_chart(self):
        interview_chart = self.talent.interviews_chart()
        self.assertTrue(isinstance(interview_chart, list))
        self.assertTrue(isinstance(interview_chart[0], MonthlyChartSchema))
        self.assertEqual(len(interview_chart), 12)


    def test_saved_jobs(self):
        self.assertEqual(self.talent.saved_jobs().count(), 0)
        SavedJob.objects.create(
            job_post=self.job_post,
            talent=self.talent
        )
        self.assertEqual(self.talent.saved_jobs().count(), 1)

    def test_applied_jobs(self):
        self.assertEqual(self.talent.applied_jobs().count(),1)

    def test_get_available_days(self):
        available_days = self.talent.get_available_days()
        self.assertTrue(isinstance(available_days, list))
        self.assertTrue(isinstance(available_days[0],dict))
        self.assertIn("day", available_days[0])
        self.assertIn("availability", available_days[0])
        self.assertEqual(type(available_days[0]["availability"]), TalentAvailableDaySchema)


