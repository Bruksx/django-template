from datetime import timedelta

from django.test import TestCase

from accounts.models import Talent
from factories import ConversationFactory, JobPostFactory, JobApplicationFactory, TalentFactory, \
    RequiredAttributeFactory, CountryFactory, BusinessUserFactory
from jobs.models import JobApplication
from notification.enums import EntityActionType
from notification.models import Notification
from notification.notifications import send_new_chat_notification, send_job_post_application_notification, \
    send_talent_job_matching_notification, \
    send_talents_job_matching_notification, send_job_sharing_notification, send_job_performance_notification, \
    send_business_user_notification, send_job_post_assignment_notification

from apps.factories import WorkflowStageFactory


class TestSendNewChatNotification(TestCase):
    def setUp(self):
        self.chat = ConversationFactory.create()

    def test_send_new_chat_notification(self):
        notification_count = Notification.objects.all().count()
        send_new_chat_notification(self.chat)
        self.assertEqual(Notification.objects.count(), notification_count + 1)

    def test_when_chat_is_none(self):
        notification_count = Notification.objects.all().count()
        send_new_chat_notification(None)
        self.assertEqual(Notification.objects.count(), notification_count)





class TestSendJobApplicationNotification(TestCase):
    def setUp(self):
        self.job_post = JobPostFactory.create()

    def test_send_job_application_notification(self):
        notification_count = Notification.objects.all().count()
        JobApplicationFactory.create(job_post=self.job_post)
        start_date = self.job_post.created_at - timedelta(days=1)
        end_date = self.job_post.created_at + timedelta(hours=1)
        send_job_post_application_notification(self.job_post, start_date, end_date)
        self.assertEqual(Notification.objects.count(), notification_count + 1)

    def test_when_no_applications(self):
        notification_count = Notification.objects.all().count()
        start_date = self.job_post.created_at - timedelta(days=1)
        end_date = self.job_post.created_at + timedelta(hours=1)
        send_job_post_application_notification(self.job_post, start_date, end_date)
        self.assertEqual(Notification.objects.count(), notification_count)


class TestSendTalentJobMatchingNotification(TestCase):
    def setUp(self):
        self.country = CountryFactory.create()
        self.job_post = JobPostFactory.create(country=self.country)
        self.talent = TalentFactory.create(country=self.country)
        self.job_post.job.requiredattribute.update(location=True,
                                        working_hours=False, years_of_experience=False,
                                        role=False, minimum_education_level=False, work_structure=False,
                                        technological_requirement=False, job_level=False,
                                        first_language=False, secondary_language=False)
        self.job_post.job.refresh_from_db()
        self.job_post.refresh_from_db()

    def test_send_talent_job_matching_notification(self):
        notification_count = Notification.objects.all().count()
        send_talent_job_matching_notification(self.talent, self.job_post)
        self.assertEqual(Notification.objects.count(), notification_count)

    def test_when_talent_score_is_low(self):
        notification_count = Notification.objects.all().count()
        self.job_post.job.requiredattribute.update(location=False,
                                        working_hours=True, years_of_experience=True,
                                        role=True, minimum_education_level=True, work_structure=True,
                                        technological_requirement=True, job_level=True,
                                        first_language=True, secondary_language=True)
        self.job_post.job.refresh_from_db()
        self.job_post.refresh_from_db()
        send_talent_job_matching_notification(self.talent, self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count)

    def test_when_called_twice(self):
        notification_count = Notification.objects.all().count()
        send_talent_job_matching_notification(self.talent, self.job_post)
        send_talent_job_matching_notification(self.talent, self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count)

class TestSendTalentsJobMatchingNotification(TestCase):
    def setUp(self):
        self.job_post = JobPostFactory.create()

    def test_send_talents_job_matching_notification(self):
        notification_count = Notification.objects.all().count()
        send_talents_job_matching_notification(6, self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count+1)

    def test_when_talent_count_is_zero(self):
        notification_count = Notification.objects.all().count()
        send_talents_job_matching_notification(0, self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count)

class TestSendJobSharingNotification(TestCase):
    def setUp(self):
        self.job_post = JobPostFactory.create()
        self.metrics = self.job_post.jobpostmetrics
        self.metrics.update(daily_email_shares=1, weekly_views=1)

    def test_send_job_sharing_notification(self):
        notification_count = Notification.objects.all().count()
        send_job_sharing_notification(self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count + 1)

    def test_where_shares_is_zero(self):
        notification_count = Notification.objects.all().count()
        self.metrics.update(daily_email_shares=0)
        send_job_sharing_notification(self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count)


class TestSendJobPerformanceNotification(TestCase):
    def setUp(self):
        self.job_post = JobPostFactory.create()
        self.metrics = self.job_post.jobpostmetrics
        self.metrics.update(job_post=self.job_post, daily_email_shares=1)
        self.stage = WorkflowStageFactory.create()
        JobApplicationFactory.create(job_post=self.job_post, stage=self.stage)
        TalentFactory.create()

    def test_send_job_performance_notification(self):
        notification_count = Notification.objects.all().count()
        send_job_performance_notification(self.job_post)
        self.assertEqual(Notification.objects.all().count(), 1 + notification_count)

    def test_where_all_metrics_are_zero(self):
        notification_count = Notification.objects.all().count()
        self.metrics.update(weekly_views=0)
        JobApplication.objects.all().delete()
        Talent.objects.all().delete()
        send_job_performance_notification(self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count)

    def test_where_no_metrics(self):
        notification_count = Notification.objects.all().count()
        self.metrics.delete()
        send_job_performance_notification(self.job_post)
        # because application metric exists
        self.assertEqual(Notification.objects.all().count(), notification_count + 1)


class TestSendBusinessUserNotification(TestCase):
    def setUp(self):
        self.business_user = BusinessUserFactory.create()

    def test_send_business_user_notification(self):
        self.assertEqual(Notification.objects.all().count(), 0)
        send_business_user_notification(self.business_user, EntityActionType.NEW, "has joined the business")
        self.assertEqual(Notification.objects.all().count(), 1)

    def test_where_no_user(self):
        send_business_user_notification(None, EntityActionType.NEW, "has joined the business")
        self.assertEqual(Notification.objects.all().count(), 0)

    def test_where_no_action(self):
        send_business_user_notification(self.business_user, None, "has joined the business")
        self.assertEqual(Notification.objects.all().count(), 0)


class TestSendJobPostAssignmentNotification(TestCase):
    def setUp(self):
        self.job_post = JobPostFactory.create()
        self.settings = self.job_post.recruiter.businessusernotificationsettings
        self.settings.update(assignment_notification=True)

    def test_send_job_post_assignment_notification(self):
        notification_count = Notification.objects.all().count()
        send_job_post_assignment_notification(self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count + 1)

    def test_where_we_have_previous_recruiter(self):
        previous_recruiter = BusinessUserFactory.create()
        previous_recruiter.businessusernotificationsettings.update(assignment_notification=True)
        notification_count = Notification.objects.all().count()
        send_job_post_assignment_notification(self.job_post, previous_recruiter)
        self.assertEqual(Notification.objects.all().count(), notification_count + 2)

    def test_where_settings_are_disabled(self):
        self.settings.update(assignment_notification=False)
        notification_count = Notification.objects.all().count()
        send_job_post_assignment_notification(self.job_post)
        self.assertEqual(Notification.objects.all().count(), notification_count)