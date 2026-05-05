import uuid
from datetime import time
from decimal import Decimal, ROUND_HALF_UP
from random import choice
from uuid import uuid4

from django.db import models
from django.test import TestCase
from django.utils import timezone
from future.backports.datetime import timedelta
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from accounts.enums import Days
from accounts.models import Department, Role, Business, Industry, BusinessUser, Skill, User, Country, Talent, \
    EducationLevel, SkillCategory, Experience, TalentAvailableDay
from core.models import City, State
from core.models import Currency
from factories import BusinessFactory, BusinessUserFactory, TalentFactory, JobPostFactory, RequiredAttributeFactory, \
    JobFactory, JobApplicationFactory, WorkflowStageFactory, UserFactory, CountryFactory, ScreeningQuestionFactory, \
    AnswerFactory, CurrencyFactory, ExperienceFactory
from jobs.external_views import router
from jobs.enums import JobStatusType, PhaseType, QuestionTypeEnum, ActionType
from jobs.models import (
    Job, AvailableDay, JobPost, ScreeningQuestion, QuestionOption, Language, EmploymentType, JobLevel, JobApplication,
    BusinessModel, RequiredSkill, RequiredAttribute, RequiredSecondaryLanguage, JobPostTag
)
from jobs.queries import add_application_match_score
from settings.models import WorkFlowStage


class EmploymentTypeListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "job-posts/indeed-pool.xml"
        self.user = UserFactory()
        JobPostFactory.create(
            status=JobStatusType.POSTED.value
        )

    def test_cdata(self):
        self.client.get(self.url, auth=self.user)