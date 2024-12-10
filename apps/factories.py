import datetime

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from accounts.enums import GenderType, PreferredCommunicationType, BusinessUserRoleType, Days
from accounts.models import User, Talent, Business, BusinessUser, Education, Role, TalentAvailableDay, CustomerCase, \
    EducationLevel, Industry, Country, AdditionalSkill, Department, Experience, Skill, SkillCategory
from settings.models import WorkFlowStage, EmailTemplate
from chats.models import Conversation, Message

fake = Faker()
from core.models import Currency, Language
from jobs.enums import WorkStructureEnum, LunchBreakEnum, WithdrawalFeedbackType, PhaseType
from jobs.models import JobLevel, EmploymentType, JobPost, Job, JobApplication, Qualification, JobApplicationWithdrawal, \
    RequiredAttribute, JobFilter, BusinessModel


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = Country

    code = factory.Faker('country_code')
    name = factory.Faker('country')
class CurrencyFactory(DjangoModelFactory):
    class Meta:
        model = Currency

    abbreviation = factory.Faker('currency_code')
    name = factory.Faker('currency_name')

class LanguageFactory(DjangoModelFactory):
    class Meta:
        model = Language

    code = factory.Faker('language_code')
    name = factory.Faker('language_name')

class JobLevelFactory(DjangoModelFactory):
    class Meta:
        model = JobLevel

    name = factory.LazyAttribute(lambda _: fake.name()[:15])


class EmploymentTypeFactory(DjangoModelFactory):
    class Meta:
        model = EmploymentType

    name = factory.Faker("name")

class IndustryFactory(DjangoModelFactory):
    class Meta:
        model = Industry

    name = factory.Faker('company')


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department

    name = factory.Faker("name")
    industry = factory.SubFactory(IndustryFactory)

class SkillCategoryFactory(DjangoModelFactory):
    name = factory.Faker("name")
    class Meta:
        model = SkillCategory

class SkillFactory(DjangoModelFactory):
    name = factory.Faker("name")
    category = factory.SubFactory(SkillCategoryFactory)
    department = factory.SubFactory(DepartmentFactory)

    class Meta:
        model = Skill

class BusinessModelFactory(DjangoModelFactory):
    name = factory.Faker("name")
    description = factory.Faker('sentence', nb_words=20)

    class Meta:
        model = BusinessModel

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name', )
    last_name = factory.Faker('last_name')
    gender = factory.Iterator(GenderType.values())
    email  = factory.Sequence(lambda n: f'user{n}@example.com')
    phone_number = factory.LazyAttribute(lambda _: fake.phone_number()[:15])
    password = factory.Faker('password')


class EducationLevelFactory(DjangoModelFactory):
    class Meta:
        model = EducationLevel

    industry = factory.SubFactory(IndustryFactory)
    level = factory.Faker("name")

class TalentFactory(DjangoModelFactory):
    class Meta:
        model = Talent

    user = factory.SubFactory(UserFactory)
    country = factory.SubFactory(CountryFactory)
    preferred_communication = factory.Iterator(PreferredCommunicationType.values())

    @factory.post_generation
    def education(self, create, extracted, **kwargs):
        EducationFactory(talent=self)
        EducationFactory(talent=self)
        ExperienceFactory(talent=self)
        ExperienceFactory(talent=self)
        ExperienceFactory(talent=self)


class AdditionalSkillFactory(DjangoModelFactory):
    class Meta:
        model = AdditionalSkill

    talent = factory.SubFactory(TalentFactory)
    name = factory.Faker("name")



class RoleFactory(DjangoModelFactory):
    class Meta:
        model = Role

    name = factory.Faker("job")
    department = factory.SubFactory(DepartmentFactory)

class BusinessFactory(DjangoModelFactory):
    class Meta:
        model = Business
    created_by = factory.SubFactory(UserFactory)
    size = factory.Iterator([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    description = factory.Faker('sentence', nb_words=20)
    website = factory.Faker('url')
    address = factory.Faker('address')
    country = factory.SubFactory(CountryFactory)
    industry = factory.Faker("company")
    name = factory.Faker('company')

class BusinessUserFactory(DjangoModelFactory):
    class Meta:
        model = BusinessUser
    business = factory.SubFactory(BusinessFactory)
    user = factory.SubFactory(UserFactory)
    role = factory.Iterator(BusinessUserRoleType.values())

class EducationFactory(DjangoModelFactory):
    class Meta:
        model = Education

    talent = factory.SubFactory(TalentFactory)
    start_date = factory.Faker('date_this_decade', before_today=True)
    end_date = factory.Faker('date_this_decade', before_today=True)
    major = factory.lazy_attribute(lambda _: fake.job()[:20])
    level = factory.SubFactory(EducationLevelFactory)
    university = factory.lazy_attribute(lambda _: fake.sentence()[:20])

class ExperienceFactory(DjangoModelFactory):
    class Meta:
        model = Experience

    talent = factory.SubFactory(TalentFactory)
    start_date = factory.Faker('date_this_decade', before_today=True)
    end_date = factory.Faker('date_this_decade', before_today=True)
    company = factory.Faker('company')
    currently_works_here = factory.Faker('pybool')
    annual_salary = factory.Faker('pyfloat', min_value=4, max_value=6, positive=True)
    annual_salary_currency = factory.SubFactory(CurrencyFactory)
    annual_salary_bonus = factory.Faker('pyfloat', min_value=4, max_value=6, positive=True)
    annual_salary_bonus_currency = factory.SubFactory(CurrencyFactory)
    level = factory.SubFactory(JobLevelFactory)
    role = factory.SubFactory(RoleFactory)
    employment_type = factory.SubFactory(EmploymentTypeFactory)

class TalentAvailableDayFactory(DjangoModelFactory):
    class Meta:
        model = TalentAvailableDay

    talent = factory.SubFactory(TalentFactory)
    day = factory.Iterator(Days.values())
    start_time = factory.Faker('time')
    end_time = factory.Faker('time')



class CustomerCaseFactory(DjangoModelFactory):
    class Meta:
        model = CustomerCase

    reason = factory.Faker('sentence', nb_words=50)
    subject = factory.Faker('sentence', nb_words=20)
    description = factory.Faker('sentence', nb_words=100)
    user = factory.SubFactory(UserFactory)

class QualificationFactory(DjangoModelFactory):
    class Meta:
        model = Qualification

    name = factory.LazyAttribute(lambda _: fake.name())


class JobFactory(DjangoModelFactory):
    class Meta:
        model = Job
    created_by = factory.SubFactory(BusinessUserFactory)
    hiring_company_name = factory.Faker('company')
    hiring_company_description = factory.Faker('sentence', nb_words=100)
    title = factory.lazy_attribute(lambda _: fake.sentence()[:15])
    about = factory.Faker('sentence', nb_words=100)
    years_of_experience = factory.Faker('pyint', min_value=1, max_value=10)
    minimum_education_level = factory.SubFactory(EducationLevelFactory)
    job_level = factory.SubFactory(JobLevelFactory)
    qualification = factory.SubFactory(QualificationFactory)
    role = factory.SubFactory(RoleFactory)
    work_structure = factory.Iterator(WorkStructureEnum.values())
    office_address = factory.Faker('address')
    lunch_break = factory.Iterator(LunchBreakEnum.values())
    lunch_break_time = factory.Iterator([10, 20, 30, 40])
    additional_hours_start = factory.Faker("time")
    additional_hours_end = factory.Faker("time")
    employment_type = factory.SubFactory(EmploymentTypeFactory)


class RequiredAttributeFactory(DjangoModelFactory):
    class Meta:
        model = RequiredAttribute
    job = factory.SubFactory(JobFactory)
    role = factory.Iterator([True, False])
    job_level = factory.Iterator([True, False])
    years_of_experience = factory.Iterator([True, False])
    minimum_education_level = factory.Iterator([True, False])
    work_structure = factory.Iterator([True, False])
    technological_requirement = factory.Iterator([True, False])
    first_language = factory.Iterator([True, False])
    secondary_language = factory.Iterator([True, False])
    working_hours = factory.Iterator([True, False])
    location = factory.Iterator([True, False])


class JobPostFactory(DjangoModelFactory):
    class Meta:
        model = JobPost
    job = factory.SubFactory(JobFactory)
    country = factory.SubFactory(CountryFactory)
    recruiter = factory.SubFactory(BusinessUserFactory)
    province = factory.Faker('city')
    postal_code = factory.Faker('postcode')
    date_posted = factory.Faker("date_this_decade", before_today=True)
    annual_salary_min = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_salary_max = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_salary_currency = factory.SubFactory(CurrencyFactory)
    annual_bonus_min = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_bonus_max = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_bonus_currency = factory.SubFactory(CurrencyFactory)

    @factory.post_generation
    def update_date_posted(self, created, extracted, **kwargs):
        date_posted = fake.date_this_decade(before_today=True)
        self.date_posted = datetime.datetime.combine(date_posted, timezone.now().time(), tzinfo=timezone.get_current_timezone())
        self.save(update_fields=['date_posted'])

class EmailTemplateFactory(DjangoModelFactory):
    class Meta:
        model = EmailTemplate

    sender = factory.Sequence(lambda n: f'sender{n}@example.com')
    subject = factory.lazy_attribute(lambda _: fake.sentence()[:30])
    template  = factory.lazy_attribute(lambda _: fake.sentence()[:100])
    created_by = factory.SubFactory(BusinessUserFactory)
    personal = factory.Iterator([True, False])
    delays = factory.Iterator([0, 1, 2, 3, 4, 5])
    bcc = factory.lazy_attribute(lambda _: [fake.email() for x in range(5)])
    cc = factory.lazy_attribute(lambda _: [fake.email() for x in range(5)])


class WorkflowStageFactory(DjangoModelFactory):
    class Meta:
        model = WorkFlowStage

    phase = factory.Iterator([*filter(lambda x: x not in (PhaseType.REJECTED.value, PhaseType.HIRED.value), PhaseType.values())])
    name = factory.Faker('sentence', nb_words=5)
    email_template = factory.SubFactory(EmailTemplateFactory)
    created_by = factory.SubFactory(BusinessUserFactory)
    is_active = factory.Iterator([True, False])

class JobApplicationFactory(DjangoModelFactory):
    class Meta:
        model = JobApplication
    job_post = factory.SubFactory(JobPostFactory)
    applicant = factory.SubFactory(TalentFactory)
    recruiter = factory.SubFactory(BusinessUserFactory)
    stage_date_updated = factory.Faker("date_time")

    @factory.post_generation
    def create_stage(self, create, extracted, **kwargs):
        if create:
            if not self.stage:
                self.stage = WorkflowStageFactory.create(created_by=self.recruiter)
                self.save()



class JobApplicationWithdrawalFactory(DjangoModelFactory):
    class Meta:
        model = JobApplicationWithdrawal
    job_post = factory.SubFactory(JobPostFactory)
    feedback = factory.Faker('sentence', nb_words=50)
    feedback_type = factory.Iterator(WithdrawalFeedbackType.indices())



class ConversationFactory(DjangoModelFactory):
    class Meta:
        model = Conversation

    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for user in extracted:
                self.users.add(user)
        else:
            # Create default authors if none were passed.
            user1 = UserFactory()
            user2 = UserFactory()
            self.users.add(user1, user2)

class MessageFactory(DjangoModelFactory):
    class Meta:
        model = Message

    conversation = factory.SubFactory(ConversationFactory)
    sender = factory.SubFactory(UserFactory)
    body = factory.Faker('sentence', nb_words=50)


class JobFilterFactory(DjangoModelFactory):
    class Meta:
        model = JobFilter

    talent = factory.SubFactory(TalentFactory)
    role = factory.lazy_attribute(lambda _: fake.sentence()[:20])
    years_of_experience = factory.Iterator([1,2,3,4,5,6,7])
    office_location = factory.SubFactory(CountryFactory)
    employment_type = factory.SubFactory(EmploymentTypeFactory)
    department = factory.SubFactory(DepartmentFactory)
    minimum_education_level = factory.SubFactory(EducationLevelFactory)
    location_type = factory.Iterator(WorkStructureEnum.values())
    remove_applied_jobs = factory.Iterator([True, False])

