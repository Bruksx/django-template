from datetime import timedelta

from django.test import TestCase
from django_q.models import Schedule
from factories import EmailTemplateFactory, WorkflowStageFactory, JobApplicationFactory
from jobs.enums import PhaseType


class EmailTemplateModelTest(TestCase):
    def setUp(self):
        self.template = EmailTemplateFactory.create(is_html=False)

    def test_send_date(self):
        self.assertEqual(self.template.send_date, self.template.created_at + timedelta(days=self.template.delays))

    def test_send_email_with_non_zero_delay(self):
        self.template.delays = 4
        self.template.save(update_fields=["delays"])
        context = dict()
        scheduled_task = Schedule.objects.first()
        self.assertIsNone(scheduled_task)
        emails = ["a@b.com", "c@d.com"]
        self.template.send_email(context, emails, self.template.sender)
        scheduled_task = Schedule.objects.first()
        self.assertIsNotNone(scheduled_task)

    def test_validate_placeholders(self):
        members = ["person", "animal"]
        placeholders = ["person", "animal", "house"]
        is_valid = self.template.validate_placeholders(
            members=members, placeholders=placeholders,
            raise_exception=False
        )
        self.assertTrue(is_valid)

        members = ["person", "office"]
        is_valid = self.template.validate_placeholders(
            members=members, placeholders=placeholders,
            raise_exception=False
        )
        self.assertFalse(is_valid)

        self.assertRaises(
            ValueError, self.template.validate_placeholders,
            members=members, placeholders=placeholders
        )


    def test_convert_to_template(self):
        text = "hello <user FIRST name>, im pleased to meet you"
        template = self.template.convert_to_template(text)
        self.assertEqual(template.source, "hello {{user_first_name}}, im pleased to meet you")

        text = "hello <<user>>, im pleased to meet you"
        self.assertRaises(ValueError, self.template.convert_to_template,
                          text)


    def test_validate_placeholder_usage(self):
        placeholders = ["person", "animal", "house"]
        subject = "welcome <person>!"
        template = "hi <person>, what you will be served <animal> in <house>."
        is_valid = self.template.validate_placeholder_usage(
            placeholders=placeholders,
            subject=subject,
            template=template
        )
        self.assertTrue(is_valid)

        subject = "welcome <personnel>!"
        self.assertRaises(ValueError, self.template.validate_placeholder_usage,
                          placeholders=placeholders,
                          subject=subject,
                          template=template)

        subject = "welcome <person>!"
        template = "hi <personnel>, what you will be served <animal> in <house>."

        self.assertRaises(ValueError, self.template.validate_placeholder_usage,
                          placeholders=placeholders,
                          subject=subject,
                          template=template)

class HTMLEmailTemplateModelTest(TestCase):
    def setUp(self):
        self.template = EmailTemplateFactory.create(is_html=True)

    def test_send_date(self):
        self.assertEqual(self.template.send_date, self.template.created_at + timedelta(days=self.template.delays))

    def test_send_email_with_non_zero_delay(self):
        self.template.delays = 4
        self.template.save(update_fields=["delays"])
        context = dict()
        scheduled_task = Schedule.objects.first()
        self.assertIsNone(scheduled_task)
        emails = ["a@b.com", "c@d.com"]
        self.template.send_email(context, emails, self.template.sender)
        scheduled_task = Schedule.objects.first()
        self.assertIsNotNone(scheduled_task)

    def test_validate_placeholders(self):
        members = ["person", "animal"]
        placeholders = ["person", "animal", "house"]
        is_valid = self.template.validate_placeholders(
            members=members, placeholders=placeholders,
            raise_exception=False
        )
        self.assertTrue(is_valid)

        members = ["person", "office"]
        is_valid = self.template.validate_placeholders(
            members=members, placeholders=placeholders,
            raise_exception=False
        )
        self.assertFalse(is_valid)

        self.assertRaises(
            ValueError, self.template.validate_placeholders,
            members=members, placeholders=placeholders
        )


    def test_convert_to_template(self):
        text = "hello {{user FIRST name}}, im pleased to meet you"
        template = self.template.convert_to_template(text, is_html=True)
        self.assertEqual(template.source, "hello {{user_first_name}}, im pleased to meet you")

        text = "hello {{{{user}}}}, im pleased to meet you"
        self.assertRaises(ValueError, self.template.convert_to_template,
                          text, is_html=True)


    def test_validate_placeholder_usage(self):
        placeholders = ["person", "animal", "house"]
        subject = "welcome {{person}}!"
        template = "hi {{person}}, what you will be served {{animal}} in {{house}}."
        is_valid = self.template.validate_placeholder_usage(
            placeholders=placeholders,
            subject=subject,
            template=template,
            is_html=True
        )
        self.assertTrue(is_valid)

        subject = "welcome {{{{personnel}}}}!"
        self.assertRaises(ValueError, self.template.validate_placeholder_usage,
                          placeholders=placeholders,
                          subject=subject,
                          template=template,
                          is_html=True)

        subject = "welcome {{{{person}}}}!"
        template = "hi {{{{personnel}}}}, what you will be served {{{{{animal}}}} in <house>."

        self.assertRaises(ValueError, self.template.validate_placeholder_usage,
                          placeholders=placeholders,
                          subject=subject,
                          template=template,
                          is_html=True)


class WorkFlowStageModelTest(TestCase):
    def setUp(self):
        self.stage = WorkflowStageFactory.create(phase=PhaseType.SCREENING.value)

    def test_can_be_deactivated(self):
        self.stage.is_active = True
        self.stage.save()

        self.assertTrue(self.stage.can_be_deactivated())

        JobApplicationFactory.create(
            stage=self.stage
        )
        self.stage.refresh_from_db()
        self.assertFalse(self.stage.can_be_deactivated())





