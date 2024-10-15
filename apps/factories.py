import factory

from accounts.enums import GenderType, PreferredCommunicationType, BusinessUserRoleType, Days
from accounts.models import User, Talent, Business, BusinessUser, Education, Role, TalentAvailableDay, CustomerCase, \
    EducationLevel, Industry, Country, AdditionalSkill
from factory.django import DjangoModelFactory
import datetime

from core.models import Currency, Language
from jobs.enums import WorkStructureEnum, LunchBreakEnum
from jobs.models import JobLevel, EmploymentType, JobPost, Job, JobApplication, Qualification


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = Country

    code = factory.Faker('country_code')
    name = factory.Faker('country')
class CurrencyFactory(DjangoModelFactory):
    class Meta:
        model = Currency

    code = factory.Faker('currency_code')
    name = factory.Faker('currency_name')

class LanguageFactory(DjangoModelFactory):
    class Meta:
        model = Language

    code = factory.Faker('language_code')
    name = factory.Faker('language_name')

class JobLevelFactory(DjangoModelFactory):
    class Meta:
        model = JobLevel

    name = factory.Faker('job_level')

class EmploymentTypeFactory(DjangoModelFactory):
    class Meta:
        model = EmploymentType

    name = factory.Faker('job_level')

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('name')
    last_name = factory.Faker('name')
    email = factory.Faker('email')
    phone_number = factory.Faker('phone_number')
    password = factory.Faker('password')

    @factory.post_generation
    def talent(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.talent = extracted
            self.talent.user = self
            self.talent.save()

    @factory.post_generation
    def business(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.business = extracted
            self.business.user = self
            self.business.save()

class IndustryFactory(DjangoModelFactory):
    class Meta:
        model = Industry

    name = factory.Faker('company')

class EducationLevelFactory(DjangoModelFactory):
    class Meta:
        model = EducationLevel

    industry = factory.SubFactory(IndustryFactory)
    level = factory.Faker("name")

class TalentFactory(DjangoModelFactory):
    class Meta:
        model = Talent

    user = factory.SubFactory(UserFactory)
    gender = factory.Iterator(GenderType.choices)
    country = factory.SubFactory(CountryFactory)
    preferred_communication = factory.Iterator(PreferredCommunicationType.choices)

class AdditionalSkillFactory(DjangoModelFactory):
    class Meta:
        model = AdditionalSkill

    talent = factory.SubFactory(TalentFactory)
    name = factory.Faker("name")



class RoleFactory(DjangoModelFactory):
    class Meta:
        model = Role

    name = factory.Faker('job')

class BusinessFactory(DjangoModelFactory):
    class Meta:
        model = Business
    created_by = factory.SubFactory(UserFactory)
    size = factory.Iterator([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    description = factory.Faker('sentence', nb_words=20)
    website = factory.Faker('url')
    location = factory.Faker('address')
    industry = factory.Faker("company")
    name = factory.Faker('company')

class BusinessUserFactory(DjangoModelFactory):
    class Meta:
        model = BusinessUser
    business = factory.SubFactory(BusinessFactory)
    user = factory.SubFactory(UserFactory)
    added_by = factory.SubFactory(UserFactory)
    role = factory.Iterator(BusinessUserRoleType.choices)

class EducationFactory(DjangoModelFactory):
    class Meta:
        model = Education

    talent = factory.SubFactory(TalentFactory)
    start_date = factory.Faker('date_this_decade', before_today=True)
    end_date = factory.Faker('date_this_decade', before_today=True)
    major = factory.Faker('sentence', nb_words=20)
    level = factory.SubFactory(EducationLevelFactory)
    university = factory.Faker('sentence', nb_words=20)

class ExperienceFactory(DjangoModelFactory):
    class Meta:
        model = Education

    talent = factory.SubFactory(TalentFactory)
    start_date = factory.Faker('date_this_decade', before_today=True)
    end_date = factory.Faker('date_this_decade', before_today=True)
    company = factory.Faker('sentence', nb_words=20)
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
    day = factory.Iterator(Days.choices())
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

    talent = factory.SubFactory(TalentFactory)
    start_date = factory.Faker('date_this_decade', before_today=True)
    end_date = factory.Faker('date_this_decade', before_today=True)
    name = factory.Faker('sentence', nb_words=20)

class JobFactory(DjangoModelFactory):
    class Meta:
        model = Job
    created_by = factory.SubFactory(BusinessUserFactory)
    hiring_company_name = factory.Faker('company')
    hiring_company_description = factory.Faker('sentence', nb_words=100)
    title = factory.Faker('sentence', nb_words=20)
    about = factory.Faker('sentence', nb_words=100)
    years_of_experience = factory.Faker('pyint', min_value=1, max_value=10)
    minimum_education_level = factory.SubFactory(EducationLevelFactory)
    job_level = factory.SubFactory(JobLevelFactory)
    qualification = factory.SubFactory(QualificationFactory)
    role = factory.SubFactory(RoleFactory)
    work_structure = factory.Iterator(WorkStructureEnum.choices)
    office_address = factory.Faker('address')
    lunch_break = factory.Iterator(LunchBreakEnum.choices())
    annual_salary_min = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_salary_max = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_salary_currency = factory.SubFactory(CurrencyFactory)
    annual_bonus_min = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_bonus_max = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_bonus_currency = factory.SubFactory(CurrencyFactory)
    recruiter = factory.SubFactory(BusinessUserFactory)
    additional_hours_min = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    additional_hours_max = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    employment_type = factory.SubFactory(EmploymentTypeFactory)


class JobPostFactory(DjangoModelFactory):
    class Meta:
        model = JobPost
    job = factory.SubFactory(JobFactory)
    country = factory.SubFactory(CountryFactory)
    recruiter = factory.SubFactory(BusinessUserFactory)
    province = factory.Faker('city')
    postal_code = factory.Faker('postcode')
    annual_salary_min = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_salary_max = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_salary_currency = factory.SubFactory(CurrencyFactory)


class JobApplicationFactory(DjangoModelFactory):
    class Meta:
        model = JobApplication
    job_post = factory.SubFactory(JobPostFactory)
    applicant = factory.SubFactory(UserFactory)
    recruiter = factory.SubFactory(BusinessUserFactory)



