import os
from random import choice

import django
from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from helpers.email.utils import send_email

from accounts.enums import BusinessUserRoleType, Days, UserType
from accounts.models import Country, Department, EducationLevel, BusinessUser, Role, Skill, User, Business, Talent
from core.models import Currency
from django.db import transaction
from faker import Faker
from jobs.enums import PhaseType
from jobs.models import JobPost, EmploymentType, JobApplication, Job, JobLevel, JobApplicationWithdrawal, SavedJob
from settings.models import WorkFlowStage
from apps.jobs.enums import JobStatusType


from apps.factories import TalentFactory, BusinessFactory, BusinessUserFactory, JobFactory, JobPostFactory, \
    RequiredAttributeFactory, JobApplicationFactory, SavedJobFactory, \
    WorkflowStageFactory, EmailTemplateFactory, CustomerCaseFactory, TalentAvailableDayFactory, \
    ScreeningQuestionFactory, AnswerFactory


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
def generate_data(password='Pass1234@now', email_recipients=None, talent_amount=50,
                  business_amount=5, staff_amount=5, job_amount=3,
                  question_amount=3, max_applied_jobs=10, max_withdrawals=10,
                  max_saved_jobs=7, silent=True

                  ):
    fake = Faker()
    countries = [*Country.objects.exclude(name__iexact="Nigeria").order_by('?')[:4]]
    nigeria = Country.objects.filter(name__iexact="Nigeria").first()

    educational_levels = EducationLevel.objects.all()
    employment_type = EmploymentType.objects.all()
    job_level = JobLevel.objects.all()
    roles = Role.objects.all()
    skills = Skill.objects.all()
    qualifications = ["Bachelor's Degree", "Master's Degree"]
    currencies = Currency.objects.all()

    user_ids = []

    countries.append(nigeria)

    talent_count = Talent.objects.all().count()
    if talent_count < talent_amount:
        if not silent:
            print("creating new talents")
        talents = TalentFactory.create_batch(talent_amount-talent_count, country=nigeria)
        user_ids.extend([talent.user.id for talent in talents])

    talents = Talent.objects.all()

    count = 0
    if not silent:
        print("creating job filters for talents")
    for country in countries:
        for talent in talents[(count * 10):((count + 1) * 10)]:
            if not talent.country:
                talent.country = country
                talent.save()
            if talent.talentavailableday_set.all().count() == 0:
                create_talent_available_days(talent)
            count += 1
    # we have 50 talents from 5 different countries

    business_count = Business.objects.count()
    if business_count < business_amount:
        if not silent:
            print("creating new businesses")
        BusinessFactory.create_batch(
            business_amount - business_count, country=get_random_data(Country.objects.all())
        )

    businesses = Business.objects.all()
    # we have 5 different businesses each with 6 staffs

    for business in businesses:
        if not hasattr(business.created_by, "businessuser"):
            user_ids.append(business.created_by.id)
            BusinessUserFactory(business=business,
                                role=BusinessUserRoleType.ADMIN.value,
                                user=business.created_by,
                                )
        staff_count = business.businessuser_set.all().count()
        if staff_count < staff_amount:
            if not silent:
                print(f"creating new staffs for {business.name} ")
            staffs = BusinessUserFactory.create_batch(staff_amount - staff_count, business=business,
                                             role=BusinessUserRoleType.TEAM_MEMBER.ADMIN.value)
            user_ids.extend([staff.user.id for staff in staffs])
        staffs = business.businessuser_set.all()
        if not silent:
            print(f"creating jobs and job posts for {business.name}")
        for staff in staffs:
            job_count_per_staff = staff.job_set.all().count()
            if job_count_per_staff < job_amount:
                JobFactory.create_batch(
                    job_amount-job_count_per_staff, created_by=staff,
                    minimum_education_level=get_random_data(educational_levels),
                    job_level=get_random_data(job_level),
                    qualification=choice(qualifications),
                    role=get_random_data(roles),
                    employment_type=get_random_data(employment_type)
                )
            jobs = staff.job_set.all()
            for job in jobs:
                if job.skills.all().count() == 0:
                    job.skills.set(get_random_list(skills, 10))
                    job.save()

                # create job required attribute for all jobs:
                if not hasattr(job, "requiredattribute"):
                    RequiredAttributeFactory.create(job=job)

                for country in countries:
                    if not JobPost.objects.filter(job=job, country=country).exists():
                        JobPostFactory(
                            country=country,
                            recruiter=staff,
                            job=job,
                            annual_salary_currency=get_random_data(currencies),
                            annual_bonus_currency=get_random_data(currencies)
                        )
                question_count = job.screeningquestion_set.all().count()
                if question_count < question_amount:
                    ScreeningQuestionFactory.create_batch(question_amount-question_count, job=job)

        # now we have have 75 * 5 = 375 job posts
    if not silent:
        print("creating workflows for businesses")
    for business in businesses:
        for phase in PhaseType.values():
            staff = BusinessUser.objects.filter(user=business.created_by).first()
            color = fake.color_name()
            data = dict(created_by=staff, phase=phase, name=color)
            if not WorkFlowStage.objects.filter(created_by__business=business, phase=phase).exists():
                email_template = EmailTemplateFactory(created_by=staff)
                WorkflowStageFactory(**data, email_template=email_template)

    applications = []
    if not silent:
        print("creating applications, saved jobs and application withdrawal for talents")
    for talent in talents:
        job_posts = JobPost.objects.filter(country=talent.country).order_by("?")

        apply_count = choice(range(1, max_applied_jobs))
        save_count = choice(range(1, max_saved_jobs))
        withdrawal_count = choice(range(1, max_withdrawals))
        # apply for job posts
        for job_post in job_posts[:apply_count]:
            if not JobApplication.objects.filter(
                job_post=job_post, applicant=talent
            ).exists():
                application = JobApplicationFactory(
                    job_post=job_post,
                    applicant=talent,
                    recruiter=job_post.recruiter,
                    stage=None,
                    match=talent.job_match_score(job_post))
                applications.append(application.id)

        # save job posts
        for job_post in job_posts[apply_count:save_count+apply_count]:
            if not SavedJob.objects.filter(job_post=job_post, talent=talent).exists():
                SavedJobFactory(job_post=job_post, talent=talent)

         # withdrawal jobs
        for job_post in job_posts[(apply_count+save_count):(apply_count+save_count+withdrawal_count)]:
            if not JobApplicationWithdrawal.objects.filter(job_post=job_post, talent=talent).exists():
                JobApplicationWithdrawal(job_post=job_post, talent=talent)

    job_applications = JobApplication.objects.all().order_by("?")

    if not silent:
        print("creating questions and answers for job applications")
    for job_application in job_applications:
        questions = job_application.job_post.job.screeningquestion_set.all()
        for question in questions:
            if question.answer_set.all().count() == 0:
                AnswerFactory.create(application=job_application,
                                     question=question)
        if job_application.stage is None:
            job_application.stage = choice(
                [None, *WorkFlowStage.objects.filter(created_by__business=job_application.recruiter.business), None])
            job_application.save()


    users = User.objects.filter(type__in=(UserType.values()))
    message = ""
    if not silent:
        print("creating customer case for users")
    for user in users:
        if user.customercase_set.all().count() == 0:
            CustomerCaseFactory.create(user=user)
        if user.id in user_ids:
            user.is_active = True
            user.email_verified = True
            user.set_password(password)
            user.save()
            message = f"{message}\nName: {user.fullname}\nEmail: {user.email}\nPassword: {password}\nUser Type: {user.type}\n\n"
    if email_recipients:
        send_email(subject="Seeded Users",
                   plain_body=message,
                   emails=email_recipients)
    if not silent:
        print(message)

@transaction.atomic
def update_talent_applications_to_no_stage():
    talents = Talent.objects.all()
    for talent in talents:
        count = talent.jobapplication_set.all().count()
        if count > 2:
            applications = talent.jobapplication_set.exclude(
                stage__phase__in=(PhaseType.HIRED.value, PhaseType.REJECTED.value)
            ).order_by("?")[:2]
            ids = [app.id for app in applications]
            JobApplication.objects.filter(id__in=ids).update(stage=None)
    print("finished updating stages in job applications")
    return

def create_job_posts_in_all_countries(job):
    t_countries = Talent.objects.only("country").values_list("country_id", flat=True).distinct()
    countries = Country.objects.filter(id__in=t_countries)
    print("countries: ", countries.count())


    dollars = Currency.objects.filter(abbreviation="USD").first()
    for country in countries:
        print(f"creating job posts in {country.name}")
        if JobPost.objects.filter(job=job, country=country).count() < 5:

            JobPostFactory.create_batch(5, job=job, recruiter=job.created_by, country=country,
                                  annual_bonus_currency=dollars, annual_salary_currency=dollars)

def create_job_posts():
    jobs = Job.objects.all()
    print("jobs: ", jobs.count())
    for job in jobs:
        print("job_posts: ", job.jobpost_set.count())

        create_job_posts_in_all_countries(job)
    print("finished creating job posts")


def update_job_post_status():
    job_posts = JobPost.objects.exclude(
        status__in=(JobStatusType.CLOSED.value, JobStatusType.PAUSED.value)
    ).update(status=JobStatusType.POSTED.value)
    print("finished updating job post status")

def delete_useless_workflows():
    from settings.models import WorkFlowStage
    workflows = WorkFlowStage.objects.exclude(phase__in=PhaseType.values())
    workflows.delete()
    print("finished deleting workflows")

def assign_name_to_email_templates():
    from settings.models import EmailTemplate
    from faker import Faker

    fake = Faker()
    email_templates = EmailTemplate.objects.filter(Q(name__isnull=True) | Q(name=""))
    for email_template in email_templates:
        email_template.name = fake.color_name()[:20]
        email_template.save()
    print("finished assigning name to email templates")


@transaction.atomic
def generate_data_for_account(email, job_amount=3,
                  question_amount=3, max_applied_jobs=30, max_withdrawals=10,
                  max_saved_jobs=7, silent=True):
    fake = Faker()
    countries = [*Country.objects.exclude(name__iexact="Nigeria").order_by('?')[:10]]
    nigeria = Country.objects.filter(name__iexact="Nigeria").first()

    Department.objects.all()
    educational_levels = EducationLevel.objects.all()
    employment_type = EmploymentType.objects.all()
    job_level = JobLevel.objects.all()
    roles = Role.objects.all()
    skills = Skill.objects.all()
    qualifications = ["Bachelor's Degree", "Master's Degree"]
    currencies = Currency.objects.all()
    countries.append(nigeria)

    talents = Talent.objects.order_by("?")[:50]

    if not silent:
        print("creating job filters for talents")
    # we have 50 talents from 5 different countries
    business_user = BusinessUser.objects.filter(user__email__iexact=email).first()
    if not business_user:
        return
    business = business_user.business

    job_count_per_staff = business_user.job_set.all().count()
    if job_count_per_staff < job_amount:
        JobFactory.create_batch(
            job_amount-job_count_per_staff, created_by=business_user,
            minimum_education_level=get_random_data(educational_levels),
            job_level=get_random_data(job_level),
            qualification=choice(qualifications),
            role=get_random_data(roles),
            employment_type=get_random_data(employment_type)
        )
    jobs = Job.objects.filter(created_by__business=business).iterator()
    for job in jobs:
        if job.skills.all().count() == 0:
            job.skills.set(get_random_list(skills, 10))
            job.save()

            # create job required attribute for all jobs:
            if not hasattr(job, "requiredattribute"):
                RequiredAttributeFactory.create(job=job)

            for country in countries:
                if not JobPost.objects.filter(job=job, country=country).exists():
                    JobPostFactory(
                        country=country,
                        recruiter=business_user,
                        job=job,
                        annual_salary_currency=get_random_data(currencies),
                        annual_bonus_currency=get_random_data(currencies)
                    )
            question_count = job.screeningquestion_set.all().count()
            if question_count < question_amount:
                ScreeningQuestionFactory.create_batch(question_amount-question_count, job=job)

        # now we have have 75 * 5 = 375 job posts
    if not silent:
        print("creating workflows for businesses")
    for phase in PhaseType.values():
        staff = BusinessUser.objects.order_by("?").first()
        color = fake.color_name()
        data = dict(created_by=staff, phase=phase, name=color)
        if not WorkFlowStage.objects.filter(created_by__business=business, phase=phase).exists():
            email_template = EmailTemplateFactory(created_by=staff)
            WorkflowStageFactory(**data, email_template=email_template)

    if not silent:
        print("creating applications, saved jobs and application withdrawal for talents")
    new_stage = WorkFlowStage.objects.filter(phase=PhaseType.NEW.value, created_by__business=business).first()
    for talent in talents:
        job_posts = JobPost.objects.filter(country=talent.country, job__created_by__business=business).order_by("?")

        apply_count = max_applied_jobs
        save_count = max_saved_jobs
        withdrawal_count = max_withdrawals

        # apply for job posts
        for job_post in job_posts[:apply_count]:
            if not JobApplication.objects.filter(
                job_post=job_post, applicant=talent
            ).exists():
                JobApplicationFactory(
                    job_post=job_post,
                    applicant=talent,
                    recruiter=job_post.recruiter,
                    stage=new_stage,
                    match=talent.job_match_score(job_post))


        # save job posts
        for job_post in job_posts[apply_count:save_count+apply_count]:
            if not SavedJob.objects.filter(job_post=job_post, talent=talent).exists():
                SavedJobFactory(job_post=job_post, talent=talent)

         # withdrawal jobs
        for job_post in job_posts[(apply_count+save_count):(apply_count+save_count+withdrawal_count)]:
            if not JobApplicationWithdrawal.objects.filter(job_post=job_post, talent=talent).exists():
                JobApplicationWithdrawal(job_post=job_post, talent=talent)

    job_applications = JobApplication.objects.filter(recruiter__business=business)

    if not silent:
        print("creating questions and answers for job applications")
    for job_application in job_applications:
        questions = job_application.job_post.job.screeningquestion_set.all()
        for question in questions:
            if question.answer_set.all().count() == 0:
                AnswerFactory.create(application=job_application,
                                     question=question)
