from collections.abc import Iterable
from datetime import date, timezone, datetime
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.enums import BusinessUserRoleType, Days
from accounts.models import User, Talent, Skill, Department, Experience, Role, Education, EducationLevel, \
    BusinessUser, Business, Country, TalentAvailableDay, BusinessIndustry, State, City
from accounts.schemas.talent import TalentSkillSchema, MonthlyChartSchema, TalentAvailableDaySchema
from chats.models import Conversation, Message
from core.models import Currency
from factories import JobPostFactory, TalentFactory, JobApplicationFactory, JobApplicationWithdrawalFactory, \
    BusinessFactory, BusinessUserFactory, CountryFactory, CurrencyFactory, JobFactory, ConversationFactory, \
    MessageFactory, ExperienceFactory, WorkflowStageFactory
from jobs.enums import LunchBreakEnum, WorkStructureEnum, PhaseType, JobStatusType
from jobs.models import JobLevel, EmploymentType, Job, JobPost, RequiredAttribute, BusinessModel, AvailableDay, \
    JobApplication, JobInterview, SavedJob
from pyasn1_modules.rfc5280 import postal_code

from settings.models import WorkFlowStage

from core.models import State


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
        self.country = Country.objects.first()
        self.state = State.objects.first()
        self.city = City.objects.first()
        self.role = Role.objects.first()
        self.currency = Currency.objects.first()
        self.job_level = JobLevel.objects.first()
        self.employment_type = EmploymentType.objects.first()
        self.education_level = EducationLevel.objects.first()
        self.country = Country.objects.first()
        self.province = State.objects.first()
        self.industry = BusinessIndustry.objects.first()
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
            user=self.user,
            country=self.country,
            state=self.state,
            city=self.city,
            postal_code="po 12345",
            bio="hello",
            linkedin="https://loklo@linkedin.com",
            notice_period=1,
            additional_skills=["django", "css"],
        )
        self.talent.photo = SimpleUploadedFile("t.jpg", b'rggggg', "image/jpg")
        self.talent.cv = SimpleUploadedFile("c.pdf", b'rggggg', "application/pdf")
        
        self.talent.save()
        self.business = Business.objects.create(
            created_by=self.user2,
            name="Example Business",
            size=50,
            description="A sample business description.",
            website="https://example.com",
            address="Lekki, Lagos, Nigeria",
            country=Country.objects.first().uid,
            industry=self.industry,
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
            salary = 700,
            salary_currency=self.currency,
            salary_bonus=700,
            salary_bonus_currency=self.currency,
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
            role=self.role,
            job_level=self.job_level,
            employment_type=self.employment_type,
            hiring_company_name="Example Company",
            title="Software Engineer",
            about="We are looking for a passionate...",  # Truncated for brevity
            years_of_experience=3,
            lunch_break=LunchBreakEnum.PAID.value,  # Assuming LunchBreakEnum has a PAID option
            availability_timezone=timezone.utc  # Set to UTC for this example
        )
        self.job_post = JobPost.objects.create(
            job=job,
            status=JobStatusType.CLOSED.value,  # Can be changed to True for posting
            country=self.country,
            province=self.province,
            postal_code="M5V 1T6",  # Replace with actual postal code
            salary_min=Decimal('80000.00'),  # Use Decimal for money fields
            salary_max=Decimal('100000.00'),
            salary_currency=self.currency,
            recruiter=self.business_user
        )
        job.requiredattribute.update(
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
        stage = WorkflowStageFactory.create(phase=PhaseType.INTERVIEW.value, created_by=self.business_user)
        job.requiredattribute.skills.set(Skill.objects.all()[:2])
        job.requiredattribute.business_models.set(BusinessModel.objects.all()[:2])
        job.requiredattribute.save()
        job.refresh_from_db()
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
        stage = stage
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
        
    def test_is_profile_completed(self):
        self.talent.validate_profile_completed()
        self.assertTrue(self.talent.is_profile_completed())
       

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
            salary=700,
            salary_currency=self.currency,
            salary_bonus=700,
            salary_bonus_currency=self.currency,
            level=self.job_level,
            employment_type=self.employment_type,
            start_date=date(year=2020, month=1, day=1),
            end_date=date(year=2023, month=1, day=1),
            currently_works_here=False
        )
        years_of_experience = self.talent.years_of_experience
        self.assertTrue(isinstance(years_of_experience, int))
        self.assertEqual(int(years_of_experience), 4)

    def test_education_history(self):
        education = self.talent.education_history()
        self.assertEqual(education.count(), 1)


    """def test_job_post_matches(self):
        job_post_matches = self.talent.job_post_matches()
        self.assertEqual(job_post_matches.count(), 1)"""

    def test_job_match_score(self):
        match_score = self.talent.job_match_score(self.job_post)
        self.talent.business_models.set(BusinessModel.objects.all()[:3])
        self.talent.refresh_from_db()
        self.job_post.job.requiredattribute.update(secondary_language=False)
        self.job_post.job.refresh_from_db()
        self.job_post.refresh_from_db()

    def test_job_applications(self):
        applications = self.talent.job_applications()
        self.assertEqual(applications.count(), 1)
        start_date = date(year=2020, month=1, day=1)
        end_date = date(year=2023, month=1, day=1)
        applications = self.talent.job_applications(start_date=start_date, end_date=end_date)
        self.assertEqual(applications.count(), 0)




    def test_invitations_to_apply(self):
        invitations =  self.talent.invitations_to_apply()
        self.assertEqual(invitations, 0)

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

    def test_dashboard_charts(self):
        dashboard_chart = self.talent.dashboard_charts()
        self.assertTrue(isinstance(dashboard_chart, dict))
        self.assertTrue(isinstance(dashboard_chart["applications"], list))
        self.assertTrue(isinstance(dashboard_chart["interviews"], list))
        self.assertTrue(isinstance(dashboard_chart["applications"][0], MonthlyChartSchema))
        self.assertTrue(isinstance(dashboard_chart["interviews"][0], MonthlyChartSchema))
        self.assertEqual(len(dashboard_chart["applications"]), 12)
        self.assertEqual(len(dashboard_chart["interviews"]), 12)


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

class BusinessModelTests(TestCase):
    max_data = 2
    sub_data = 1

    def setUp(self):
        business = BusinessFactory.create()
        recruiters = BusinessUserFactory.create_batch(size=self.max_data, business=business)
        self.business_user = recruiters[0]
        job_post_list = []
        country = CountryFactory.create()
        currency = CurrencyFactory.create()
        jobs = JobFactory.create_batch(
            size=self.max_data,
            created_by=recruiters[0],

        )
        index = 0
        for job in jobs:
            job.recruiter = recruiters[0]
            job.save()
            job_post_list.append(JobPostFactory.create(recruiter=recruiters[index],
                                              status=JobStatusType.POSTED.value,
                                                       country=country,
                                                       job=job))
            index += 1

        talents = TalentFactory.create_batch(size=self.max_data, country=country)
        for index in range(self.sub_data):
            conversation = ConversationFactory.create(
                users=[recruiters[index].user, talents[index].user]
            )
            MessageFactory.create(
                conversation=conversation,
                sender=recruiters[index].user,
                job_post=job_post_list[index]
            )

        for talent in talents:
            stage = WorkFlowStage.objects.filter(phase=PhaseType.NEW.value, created_by__business=business).first()
            for index in range(self.max_data):
                ExperienceFactory.create(talent=talent)
                JobApplicationFactory.create(applicant=talent, job_post=job_post_list[index], stage=stage)


        for talent in talents[:self.sub_data]:
            JobApplicationWithdrawalFactory.create(job_post=job_post_list[index], talent=talent)
        self.business = business
        self.country = country
        self.hired_stage = WorkflowStageFactory.create(phase=PhaseType.HIRED.value,
                                                  created_by=self.business_user)


    def test_total_hires(self):
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[:self.sub_data]
        self.assertEqual(self.business.total_hires(), 0)
        hired_stage = WorkFlowStage.objects.filter(phase=PhaseType.HIRED.value, created_by__business=self.business).first()
        JobApplication.objects.filter(id__in=last_sub_application_ids).update(stage=hired_stage)
        self.assertEqual(self.business.total_hires(), self.sub_data)

    def test_open_roles(self):
        self.assertEqual(self.business.total_open_roles(), self.max_data)
        first_sub_job_ids = JobPost.objects.only("id").order_by("-id").values_list("id", flat=True)[:self.sub_data]
        JobPost.objects.filter(id__in=first_sub_job_ids).update(status=JobStatusType.CLOSED.value)
        self.assertEqual(self.business.total_open_roles(), self.max_data-self.sub_data)

    def test_total_applicants(self):
        self.assertEqual(self.business.total_applicants(), self.max_data)
        talent = TalentFactory.create(country=self.country)
        last_job_post = JobPost.objects.last()
        stage = WorkFlowStage.objects.filter(phase=PhaseType.NEW.value, created_by__business=self.business).first()
        JobApplicationFactory.create(applicant=talent, job_post=last_job_post, stage=stage)
        self.assertEqual(self.business.total_applicants(), self.max_data+1)

    def test_average_days_to_hire(self):
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        self.assertEqual(self.business.average_days_to_hire(), 0)
        # days_to_hire_list = list()
        # for app_id in last_sub_application_ids:
        #     j = JobApplication.objects.get(id=app_id)
        #     j.update(stage=self.hired_stage)
        #     days_to_hire_list.append(j.)
        # self.assertAlmostEqual(self.business.average_days_to_hire(),
        #                  sum(days_to_hire_list)/self.sub_data)

    # def test_total_invitations_sent(self):
    #     self.assertEqual(self.business.total_invitations_sent(), self.sub_data)
    #     talent = Talent.objects.last()
    #     recruiter = BusinessUser.objects.last()
    #     convo = ConversationFactory.create(users=[talent.user, recruiter.user])
    #     MessageFactory.create(conversation=convo, sender=recruiter.user)
    #     self.assertEqual(self.business.total_invitations_sent(), self.sub_data)
    #     MessageFactory.create(conversation=convo, sender=recruiter.user, job_post=JobPost.objects.last())
    #     self.assertEqual(self.business.total_invitations_sent(), self.sub_data+1)


    def test_total_location_of_hires(self):
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        self.assertEqual(self.business.total_location_of_hires(), 0)
        JobApplication.objects.filter(id__in=last_sub_application_ids).update(stage=self.hired_stage)
        self.assertEqual(self.business.total_location_of_hires(), 1)

    def test_recruiter_performance(self):
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        count, _ = self.business.recruiter_performance()
        self.assertEqual(count, 0)
        JobApplication.objects.filter(id__in=last_sub_application_ids).update(stage=self.hired_stage)
        count, _ = self.business.recruiter_performance()
        self.assertEqual(count, self.sub_data)


    def test_location_of_hires(self):
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        count, _ = self.business.location_of_hires()
        self.assertEqual(count, 0)
        JobApplication.objects.filter(id__in=last_sub_application_ids).update(stage=self.hired_stage)
        count, _ = self.business.location_of_hires()
        self.assertEqual(count, 1)

    def test_hired_genders(self):
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        count, _ = self.business.hired_genders()
        self.assertEqual(count, 0)
        JobApplication.objects.filter(id__in=last_sub_application_ids).update(stage=self.hired_stage)
        count, _ = self.business.hired_genders()
        self.assertEqual(count, self.sub_data)

    def test_applicants_by_gender(self):
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        count, _ = self.business.applicants_by_gender()
        self.assertEqual(count, 2)
        JobApplication.objects.filter(id__in=last_sub_application_ids).update(stage=self.hired_stage)
        count, _ = self.business.applicants_by_gender()
        self.assertEqual(count, 2)

    # def test_time_to_hire(self):
    #     last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
    #                                :self.sub_data]
    #     for app_id in last_sub_application_ids:
    #         j = JobApplication.objects.get(id=app_id)
    #         j.update(stage=self.hired_stage)
    #     data = self.business.time_to_hire()
    #     self.assertGreater(len(data), 0)

    def test_withdrawal_reasons(self):
        count, _ = self.business.withdrawal_reasons()
        self.assertEqual(count, self.sub_data * self.sub_data)
        job_post = JobPost.objects.last()
        talent = Talent.objects.last()
        JobApplicationWithdrawalFactory.create(job_post=job_post, talent=talent)
        count, _ = self.business.withdrawal_reasons()
        self.assertEqual(count, (self.sub_data * self.sub_data)+1)

    def test_hires_last_3_months(self):
        data = self.business.hires_last_3_months()
        self.assertEqual(len(data), 0)
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        for app_id in last_sub_application_ids:
            j = JobApplication.objects.get(id=app_id)
            j.update(stage=self.hired_stage)
        data = self.business.hires_last_3_months()
        self.assertEqual(len(data), self.sub_data)

    def test_applicants_years_of_experience(self):
        data = self.business.applicants_years_of_experience()
        self.assertEqual(len(data), 7)


    def test_talent_at_each_phase(self):
        data = self.business.talent_at_each_phase()
        hired_phase = list(filter(lambda x: x["phase"] == PhaseType.HIRED.value, data))[0]
        self.assertEqual(hired_phase["count"], 0)
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        JobApplication.objects.filter(id__in=last_sub_application_ids).update(stage=self.hired_stage)
        data = self.business.talent_at_each_phase()
        hired_phase = list(filter(lambda x: x["phase"] == PhaseType.HIRED.value, data))[0]
        self.assertEqual(hired_phase["count"], self.sub_data)

    def test_talent_at_each_stage(self):
        data = self.business.talent_at_each_stage()
        self.assertIn("stage", data[0])
        self.assertIn("count", data[0])

    def test_time_to_hire_stage(self):
        data = self.business.time_to_hire_via_stage()
        self.assertEqual(data, list())
        last_sub_application_ids = JobApplication.objects.only("id").order_by("-id").values_list("id", flat=True)[
                                   :self.sub_data]
        applications = JobApplication.objects.filter(id__in=last_sub_application_ids)
        for application in applications:
            application.update(stage=self.hired_stage)
        data = self.business.time_to_hire_via_stage()
        self.assertNotEqual(data, list())
        self.assertIn("role", data[0])
        self.assertIn("graph" , data[0])
        self.assertIn("days_to_hire", data[0])
        print(data[0]["graph"])
        self.assertTrue(isinstance(data[0]["graph"], Iterable))
        self.assertIn("stage", data[0]["graph"][0])
        self.assertIn("avg_timeline", data[0]["graph"][0])

