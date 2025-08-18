import datetime
import random
from random import choice

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from accounts.enums import GenderType, PreferredCommunicationType, BusinessUserRoleType, Days
from accounts.models import User, Talent, Business, BusinessUser, Education, Role, TalentAvailableDay, CustomerCase, \
    EducationLevel, Industry, Country, Department, Experience, Skill, SkillCategory, BusinessIndustry, TalentFilter
from chats.models import Conversation, Message
from notification.enums import EntityActionType, EntityType, NotificationType
from notification.models import BusinessUserNotificationSettings, Notification
from settings.models import WorkFlowStage, EmailTemplate

fake = Faker()
from core.models import Currency, Language, City, State
from jobs.enums import WorkStructureEnum, LunchBreakEnum, WithdrawalFeedbackType, PhaseType, QuestionTypeEnum
from jobs.models import JobLevel, EmploymentType, JobPost, Job, JobApplication, JobApplicationWithdrawal, \
    RequiredAttribute, BusinessModel, ScreeningQuestion, Answer, QuestionOption, JobPostMetrics, SavedJob


class BaseModelFactory(DjangoModelFactory):
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)

    class Meta:
        abstract = True


class CountryFactory(BaseModelFactory):
    class Meta:
        model = Country

    code = factory.Faker('country_code')
    name = factory.Faker('country')


class StateFactory(BaseModelFactory):
    class Meta:
        model = State

    name = factory.Faker('state')
    country = factory.SubFactory(CountryFactory)

class CityFactory(BaseModelFactory):
    class Meta:
        model = City

    name = factory.Faker('city')
    state = factory.SubFactory(StateFactory)




class CurrencyFactory(BaseModelFactory):
    class Meta:
        model = Currency

    abbreviation = factory.Faker('currency_code')
    name = factory.Faker('currency_name')

class LanguageFactory(BaseModelFactory):
    class Meta:
        model = Language

    name = factory.Faker('language_name')

class JobLevelFactory(BaseModelFactory):
    class Meta:
        model = JobLevel

    name = factory.LazyAttribute(lambda _: fake.name()[:15])


class EmploymentTypeFactory(BaseModelFactory):
    class Meta:
        model = EmploymentType

    name = factory.Faker("name")

class IndustryFactory(BaseModelFactory):
    class Meta:
        model = Industry

    name = factory.Faker('company')


class DepartmentFactory(BaseModelFactory):
    class Meta:
        model = Department

    name = factory.Faker("name")
    industry = factory.SubFactory(IndustryFactory)

class SkillCategoryFactory(BaseModelFactory):
    name = factory.Faker("name")
    class Meta:
        model = SkillCategory

class SkillFactory(BaseModelFactory):
    name = factory.Faker("name")
    category = factory.SubFactory(SkillCategoryFactory)
    department = factory.SubFactory(DepartmentFactory)

    class Meta:
        model = Skill

class BusinessModelFactory(BaseModelFactory):
    name = factory.Faker("name")
    description = factory.Faker('sentence', nb_words=20)

    class Meta:
        model = BusinessModel

class UserFactory(BaseModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name', )
    last_name = factory.Faker('last_name')
    gender = factory.Iterator(GenderType.values())
    email  = factory.Sequence(lambda n: f'test_userx_{n}@example.com')
    phone_number = factory.LazyAttribute(lambda _: fake.phone_number()[:15])
    password = factory.Faker('password')


class EducationLevelFactory(BaseModelFactory):
    class Meta:
        model = EducationLevel

    industry = factory.SubFactory(IndustryFactory)
    level = factory.Faker("name")

class TalentFactory(BaseModelFactory):
    class Meta:
        model = Talent

    user = factory.SubFactory(UserFactory)
    country = factory.SubFactory(CountryFactory)
    preferred_communication = factory.Iterator(PreferredCommunicationType.values())


    @factory.post_generation
    def education(self, create, extracted, **kwargs):
        if not create:
            return
        EducationFactory.create_batch(
            2, talent=self,
            level=EducationLevel.objects.order_by("?").first()
                                      )
        ExperienceFactory.create_batch(
            3, talent=self,
            level=JobLevel.objects.order_by("?").first(),
            employment_type=EmploymentType.objects.order_by("?").first(),
            role=Role.objects.order_by("?").first()
        )
        return


class RoleFactory(BaseModelFactory):
    class Meta:
        model = Role

    name = factory.Faker("job")
    department = factory.SubFactory(DepartmentFactory)


class BusinessIndustryFactory(BaseModelFactory):
    name = factory.Faker("name")
    class Meta:
        model = BusinessIndustry


class BusinessFactory(BaseModelFactory):
    class Meta:
        model = Business
    created_by = factory.SubFactory(UserFactory)
    size = factory.Iterator([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    description = factory.Faker('sentence', nb_words=20)
    website = factory.Faker('url')
    address = factory.Faker('address')
    country = factory.SubFactory(CountryFactory)
    industry = factory.SubFactory(BusinessIndustryFactory)

class BusinessUserFactory(BaseModelFactory):
    class Meta:
        model = BusinessUser
    business = factory.SubFactory(BusinessFactory)
    user = factory.SubFactory(UserFactory)
    role = factory.Iterator(BusinessUserRoleType.values())

class EducationFactory(BaseModelFactory):
    class Meta:
        model = Education

    talent = factory.SubFactory(TalentFactory)
    start_date = factory.Faker('date_this_decade', before_today=True)
    end_date = factory.Faker('date_this_decade', before_today=True)
    major = factory.lazy_attribute(lambda _: fake.job()[:20])
    level = factory.SubFactory(EducationLevelFactory)
    university = factory.lazy_attribute(lambda _: fake.company()[:20])

class ExperienceFactory(BaseModelFactory):
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

class TalentAvailableDayFactory(BaseModelFactory):
    class Meta:
        model = TalentAvailableDay

    talent = factory.SubFactory(TalentFactory)
    day = factory.Iterator(Days.values())
    start_time = factory.Faker('time')
    end_time = factory.Faker('time')



class CustomerCaseFactory(BaseModelFactory):
    class Meta:
        model = CustomerCase

    reason = factory.lazy_attribute(lambda _: fake.sentence()[:100])
    subject = factory.lazy_attribute(lambda _: fake.sentence()[:100])
    description = factory.Faker('sentence', nb_words=100)
    user = factory.SubFactory(UserFactory)


class JobFactory(BaseModelFactory):
    class Meta:
        model = Job
    created_by = factory.SubFactory(BusinessUserFactory)
    hiring_company_name = factory.Faker('company')
    hiring_company_description = factory.Faker('sentence', nb_words=100)
    title = factory.lazy_attribute(lambda _: fake.job()[:15])
    about = factory.Faker('sentence', nb_words=100)
    years_of_experience = factory.Faker('pyint', min_value=1, max_value=10)
    minimum_education_level = factory.SubFactory(EducationLevelFactory)
    job_level = factory.SubFactory(JobLevelFactory)
    qualification = factory.Faker("sentence")
    role = factory.SubFactory(RoleFactory)
    work_structure = factory.Iterator(WorkStructureEnum.values())
    office_address = factory.Faker('address')
    lunch_break = factory.Iterator(LunchBreakEnum.values())
    lunch_break_time = factory.Iterator([10, 20, 30, 40])
    employment_type = factory.SubFactory(EmploymentTypeFactory)


class RequiredAttributeFactory(BaseModelFactory):
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


class JobPostFactory(BaseModelFactory):
    class Meta:
        model = JobPost
    job = factory.SubFactory(JobFactory)
    country = factory.SubFactory(CountryFactory)
    recruiter = factory.SubFactory(BusinessUserFactory)
    province = factory.SubFactory(StateFactory)
    city = factory.SubFactory(CityFactory)
    postal_code = factory.Faker('postcode')
    annual_salary_min = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_salary_max = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_salary_currency = factory.SubFactory(CurrencyFactory)
    annual_bonus_min = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_bonus_max = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    annual_bonus_currency = factory.SubFactory(CurrencyFactory)
    last_refreshed = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def update_date_posted(self, created, extracted, **kwargs):
        date_posted = fake.date_this_decade(before_today=True)
        self.date_posted = datetime.datetime.combine(date_posted, timezone.now().time(), tzinfo=timezone.get_current_timezone())
        self.save(update_fields=['date_posted'])

class EmailTemplateFactory(BaseModelFactory):
    class Meta:
        model = EmailTemplate

    name = factory.lazy_attribute(lambda _: fake.color_name()[:20])
    sender = factory.Sequence(lambda n: f'sender{n}@example.com')
    subject = factory.lazy_attribute(lambda _: fake.sentence()[:30])
    template  = factory.lazy_attribute(lambda _: fake.sentence()[:100])
    created_by = factory.SubFactory(BusinessUserFactory)
    personal = factory.Iterator([True, False])
    delays = factory.Iterator([0, 1, 2, 3, 4, 5])
    bcc = factory.lazy_attribute(lambda _: [fake.email() for x in range(5)])
    cc = factory.lazy_attribute(lambda _: [fake.email() for x in range(5)])

class SavedJobFactory(BaseModelFactory):
    class Meta:
        model = SavedJob

    job_post = factory.SubFactory(JobPostFactory)
    talent = factory.SubFactory(TalentFactory)



class WorkflowStageFactory(BaseModelFactory):
    class Meta:
        model = WorkFlowStage

    phase = factory.lazy_attribute(lambda _: choice([x for x in PhaseType.values() if x not in [PhaseType.HIRED.value, PhaseType.REJECTED.value]]))
    name = factory.lazy_attribute(lambda _: fake.color_name()[:20])
    email_template = factory.SubFactory(EmailTemplateFactory)
    created_by = factory.SubFactory(BusinessUserFactory)
    is_active = factory.Iterator([True, False])

class JobApplicationFactory(BaseModelFactory):
    class Meta:
        model = JobApplication
    stage = factory.SubFactory(WorkflowStageFactory)
    job_post = factory.SubFactory(JobPostFactory)
    applicant = factory.SubFactory(TalentFactory)
    recruiter = factory.SubFactory(BusinessUserFactory)
    stage_date_updated = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def create_stage(self, create, extracted, **kwargs):
        if not create:
            return
        if self.stage:
            return
        workflow_stage = WorkFlowStage.objects.filter(created_by__business=self.recruiter.business).order_by("?").first()
        if not workflow_stage:
            email_template = EmailTemplateFactory(created_by=self.recruiter)
            workflow_stage = WorkflowStageFactory.create(created_by=self.recruiter, email_template=email_template, phase=PhaseType.NEW.value)
        self.stage=workflow_stage
        self.save()
        return



class JobApplicationWithdrawalFactory(BaseModelFactory):
    class Meta:
        model = JobApplicationWithdrawal
    job_post = factory.SubFactory(JobPostFactory)
    feedback = factory.Faker('sentence', nb_words=50)
    feedback_type = factory.Iterator(WithdrawalFeedbackType.indices())



class ConversationFactory(BaseModelFactory):
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

class MessageFactory(BaseModelFactory):
    class Meta:
        model = Message

    conversation = factory.SubFactory(ConversationFactory)
    sender = factory.SubFactory(UserFactory)
    body = factory.Faker('sentence', nb_words=50)


class ScreeningQuestionFactory(BaseModelFactory):
    class Meta:
        model = ScreeningQuestion

    job = factory.SubFactory(JobFactory)
    text = factory.lazy_attribute(lambda _: fake.sentence()[:50])
    type = factory.Iterator(QuestionTypeEnum.values())
    is_knockout = factory.Iterator([True, False])

    @factory.post_generation
    def create_options(self, create, extracted, **kwargs):
        if not create:
            return

        if self.type == QuestionTypeEnum.SINGLE_SELECT.value:
            options = QuestionOptionFactory.create_batch(4, question=self, is_accepted=False)
            correct = random.choice(options)
            correct.is_accepted = True
            correct.save()
        elif self.type == QuestionTypeEnum.MULTI_SELECT.value:
            options = QuestionOptionFactory.create_batch(4, question=self, is_accepted=False)
            number_of_correct = random.randint(2, 4)
            correct_options = random.choices(options, k=number_of_correct)
            for option in correct_options:
                option.is_accepted = True
                option.save()
        return

class QuestionOptionFactory(BaseModelFactory):
    class Meta:
        model = QuestionOption

    question = factory.SubFactory(ScreeningQuestionFactory)
    is_accepted = factory.Iterator([True, False])
    text = factory.lazy_attribute(lambda _: fake.sentence()[:50])

class AnswerFactory(BaseModelFactory):
    class Meta:
        model = Answer

    application = factory.SubFactory(JobApplication)
    question = factory.SubFactory(ScreeningQuestionFactory)

    @factory.post_generation
    def create_other_fields(self, create, extracted, **kwargs):
        if not create:
            return
        if self.question.type == QuestionTypeEnum.SINGLE_SELECT.value:
            option = random.choice(self.question.questionoption_set.all())
            self.options.set([option])
            self.save()
        elif self.question.type == QuestionTypeEnum.MULTI_SELECT.value:
            number_of_options = random.randint(2, 4)
            options = random.choices(self.question.questionoption_set.all(), k=number_of_options)
            self.options.set(options)
            self.save()
        elif self.question.type == QuestionTypeEnum.TEXT.value:
            self.text = fake.sentence()
            self.save()

        else:
            self.files = [fake.url(), fake.url()]


class JobPostMetricsFactory(BaseModelFactory):
    class Meta:
        model = JobPostMetrics

    job_post = factory.SubFactory(JobPostFactory)
    daily_email_shares = factory.Iterator([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    weekly_views = factory.Iterator([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


class BusinessUserNotificationSettingsFactory(BaseModelFactory):
    class Meta:
        model = BusinessUserNotificationSettings

    business_user = factory.SubFactory(BusinessUserFactory)
    applicants_notification = factory.Iterator([True, False])
    matching_notification = factory.Iterator([True, False])
    sharing_notification = factory.Iterator([True, False])
    performance_notification = factory.Iterator([True, False])
    user_notification = factory.Iterator([True, False])
    assignment_notification = factory.Iterator([True, False])

class NotificationFactory(BaseModelFactory):
    class Meta:
        model = Notification

    title = factory.lazy_attribute(lambda _: fake.sentence()[:50])
    description = factory.Faker('sentence', nb_words=50)
    action = factory.Iterator(EntityActionType.values())
    entity = factory.Iterator(EntityType.values())
    entity_uid = fake.uuid4()
    entity_str = factory.lazy_attribute(lambda _: fake.sentence()[:20])
    notification_type = factory.Iterator(NotificationType.values())

class TalentFilterFactory(BaseModelFactory):
    class Meta:
        model = TalentFilter

    business_user = factory.SubFactory(BusinessUserFactory)
    role = factory.SubFactory(RoleFactory)
    industry = factory.SubFactory(IndustryFactory)
    location = factory.Faker('city')
    languages = factory.SubFactory(LanguageFactory)
    educational_level = factory.SubFactory(EducationLevelFactory)
    maximum_notice_period = factory.Faker('random_int', min=1, max=90)
    work_structure = factory.Faker('random_element', elements=[e.value for e in WorkStructureEnum])
    skills = factory.SubFactory(SkillFactory)

    @factory.post_generation
    def languages(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for language in extracted:
                self.languages.add(language)

    @factory.post_generation
    def skills(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for skill in extracted:
                self.skills.add(skill)