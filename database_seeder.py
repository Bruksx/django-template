import os
from random import choice

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from helpers.email.utils import send_email

from accounts.enums import BusinessUserRoleType, Days
from accounts.models import Country, Department, EducationLevel, BusinessUser, Role, Skill, User
from core.models import Currency
from django.db import transaction
from faker import Faker
from jobs.enums import PhaseType
from jobs.models import JobPost, EmploymentType, JobApplication, JobLevel, Qualification
from settings.models import WorkFlowStage

from apps.factories import TalentFactory, BusinessFactory, BusinessUserFactory, JobFactory, JobPostFactory, \
    RequiredAttributeFactory, JobFilterFactory, JobApplicationFactory, SavedJobFactory, \
    WorkflowStageFactory, EmailTemplateFactory, CustomerCaseFactory, TalentAvailableDayFactory


def create_talent_available_days(talent):
    start = choice(range(0, 3))
    end = choice(range(5, 7))
    for day in Days.values()[start: end]:
        TalentAvailableDayFactory(talent=talent, day=day)

def get_random_data(data):
    return data.order_by("?").first()

def get_random_list(data, count):
    return data.order_by("?")[:count]


@transaction.atomic
def generate_data(password, email_recipients):
        fake = Faker()
        countries = [*Country.objects.exclude(name__iexact="Nigeria").order_by('?')[:4]]
        nigeria = Country.objects.filter(name__iexact="Nigeria").first()

        departments =  Department.objects.all()
        educational_levels = EducationLevel.objects.all()
        employment_type = EmploymentType.objects.all()
        job_level = JobLevel.objects.all()
        roles = Role.objects.all()
        skills = Skill.objects.all()
        qualifications = Qualification.objects.all()
        currencies = Currency.objects.all()

        user_ids = []

        countries.append(nigeria)

        talents = TalentFactory.create_batch(50, country=nigeria)

        count = 0
        for country in countries:
            for talent in talents[(count * 10):((count + 1) * 10)]:
                talent.country = country
                talent.save()
                user_ids.append(talent.user.id)
                create_talent_available_days(talent)
                JobFilterFactory(talent=talent,
                                 department=get_random_data(departments),
                                 minimum_education_level=get_random_data(educational_levels),
                                 employment_type=get_random_data(employment_type),
                                 office_location=talent.country)
                talent.country = country
                talent.save()
                count += 1
        # we have 50 talents from 5 different countries

        businesses = BusinessFactory.create_batch(
            5, country=get_random_data(Country.objects.all())
        )

        # we have 5 different businesses each with 6 staffs

        for business in businesses:
            user_ids.append(business.created_by.id)
            BusinessUserFactory(business=business,
                                role=BusinessUserRoleType.ADMIN.value,
                                user=business.created_by,
                    )
            staffs = BusinessUserFactory.create_batch(5, business=business, role=BusinessUserRoleType.TEAM_MEMBER.ADMIN.value)

            for staff in staffs:
                user_ids.append(staff.user.id)
                jobs = JobFactory.create_batch(
                    3, created_by=staff,
                    minimum_education_level=get_random_data(educational_levels),
                    job_level=get_random_data(job_level),
                    qualification=get_random_data(qualifications),
                    role=get_random_data(roles),
                    employment_type=get_random_data(employment_type)
                 )

                # job count should be 15 per business, so in total 15 * 5 = 75, thats 75 jobs
                for job in jobs:
                    job.skills.set(get_random_list(skills, 10))
                    job.save()
                    # create job required attribute for all jobs:
                    RequiredAttributeFactory.create(job=job)
                    for country in countries:
                        JobPostFactory(
                            country=country,
                            recruiter=staff,
                            job=job,
                            annual_salary_currency=get_random_data(currencies),
                            annual_bonus_currency=get_random_data(currencies)
                        )
            # now we have have 75 * 5 = 375 job posts

        for business in businesses:
            for phase in PhaseType.values():
                staff = BusinessUser.objects.filter(user=business.created_by).first()
                color = fake.color_name()
                data = dict(created_by=staff, phase=phase, name=color)
                workflow = WorkFlowStage.objects.filter(**data).first()
                if not workflow:
                    email_template = EmailTemplateFactory(
                        created_by=staff
                    )
                    WorkflowStageFactory(**data, email_template=email_template)

        applications = []

        for talent in talents:
            job_posts = JobPost.objects.filter(country=talent.country).order_by("?")

            apply_count = choice(range(1, 15))
            save_count = choice(range(1, 20))
            # apply for job posts
            for job_post in job_posts[:apply_count]:
                application = JobApplicationFactory(
                    job_post=job_post,
                    applicant=talent,
                    recruiter=job_post.recruiter,
                    stage=None,
                    match=talent.job_match_score(job_post))
                applications.append(application.id)

            # save job posts
            for job_post in job_posts[:save_count]:
                SavedJobFactory(job_post=job_post, talent=talent)

        job_applications = JobApplication.objects.filter(id__in=applications).order_by("?")[:100]

        for job_application in job_applications:

            job_application.stage = choice(WorkFlowStage.objects.filter(created_by__business=job_application.recruiter.business))
            job_application.save()


        users = User.objects.filter(id__in=user_ids)
        message = ""
        for user in users:
            CustomerCaseFactory.create(user=user)
            user.is_active = True
            user.email_verified = True
            user.set_password(password)
            user.save()
            message = f"{message}\nName: {user.fullname}\nEmail: {user.email}\nPassword: {password}\nUser Type: {user.type}\n\n"


        send_email(subject="Seeded Users",
                   plain_body=message,
                   emails=email_recipients)
        print(message)

generate_data("P455@1840GTC", ["ohaegbulouis@gmail.com"])