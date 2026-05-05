import logging

from accounts.enums import BusinessUserRoleType
from accounts.enums import BusinessUserRoleType
from accounts.enums import BusinessUserRoleType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from factories import BusinessUserFactory, EmailTemplateFactory, WorkflowStageFactory, JobApplicationFactory, \
    TalentFactory
from factories import BusinessUserFactory, EmailTemplateFactory, WorkflowStageFactory, JobApplicationFactory, TalentFactory
from jobs.enums import PhaseType
from jobs.models import JobApplication
from ninja.testing import TestClient
from settings.enums import PlaceHolderType
from settings.models import EmailTemplate, WorkFlowStage, EmailTemplateAttachment
from settings.views import router


class TestCreateEmailTemplate(TestCase):
    def setUp(self):
        self.client = self.client
        self.client = TestClient(router)
        self.url = "email-templates"
        self.business_user = BusinessUserFactory.create()
        file_data = SimpleUploadedFile(
            "test_file.txt", b"This is a test file", content_type="text/plain"
        )

        self.test_data = {
            "name": "Test Template",
            "sender": "info@example.com",
            "subject": f"Welcome <{PlaceHolderType.CANDIDATE_FULLNAME.value}>!",
            "template": f"Hi <{PlaceHolderType.CANDIDATE_FULLNAME.value}>, welcome to our company. Please contact us at <{PlaceHolderType.YOUR_COMPANY_NAME.value}>.",
            "placeholders": ",".join([PlaceHolderType.CANDIDATE_FULLNAME.value, PlaceHolderType.YOUR_COMPANY_NAME.value]),
            "delays": 2,
            "bcc": ",".join(["bob@example.com", "joe@example.com"]),
            "cc": ",".join(["pitt@example.com"]),
            "personal": True,
            "attachments": [file_data],
        }


    def test_create_email_template(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = self.test_data

        template = EmailTemplate.objects.first()
        self.assertIsNone(template)
        response = self.client.post(self.url, data=data,
                                    headers=headers,
                                    content_type="multipart/form-data")
        self.assertEqual(response.status_code, 201)
        template = EmailTemplate.objects.first()
        self.assertEqual(template.name, data["name"])
        self.assertEqual(template.sender, data["sender"])
        self.assertEqual(template.delays, data["delays"])
        self.assertEqual(template.personal, data["personal"])
        self.assertEqual(template.created_by, self.business_user)

    def test_create_email_template_without_bcc_and_cc(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = self.test_data
        del data["bcc"]
        del data["cc"]

        template = EmailTemplate.objects.first()
        self.assertIsNone(template)
        response = self.client.post(self.url, data=data,
                                    headers=headers,
                                    content_type="multipart/form-data")
        self.assertEqual(response.status_code, 201)
        template = EmailTemplate.objects.first()
        self.assertEqual(template.name, data["name"])
        self.assertEqual(template.sender, data["sender"])
        self.assertEqual(template.delays, data["delays"])
        self.assertEqual(template.personal, data["personal"])
        self.assertEqual(template.created_by, self.business_user)

    def test_for_invalid_subject_placeholder(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = self.test_data
        data["subject"] = "hello <candidate_name>!"
        response = self.client.post(self.url, data=data,
                                    headers=headers,
                                    format="multipart/form-data")

        self.assertEqual(response.status_code, 400)

    def test_for_invalid_subject_placeholder_format(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = self.test_data
        data["subject"] = f"hello <<{PlaceHolderType.CANDIDATE_FULLNAME.value}>>!"
        response = self.client.post(self.url, data=data,
                                    headers=headers,
                                    format="multipart/form-data")

        self.assertEqual(response.status_code, 400)

    def test_create_template_with_same_name(self):
        EmailTemplateFactory.create(name="Test Template", created_by=self.business_user, personal=self.test_data["personal"])
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = self.test_data
        response = self.client.post(self.url, data=data,
                                    headers=headers,
                                    format="multipart/form-data")

        self.assertEqual(response.status_code, 400)


class TestUpdateEmailTemplate(TestCase):
    def setUp(self):
        self.client = self.client
        self.client = TestClient(router)
        self.url = lambda uid : f"email-templates/{uid}"
        self.business_user = BusinessUserFactory.create()

        file_data = SimpleUploadedFile(
            "test_file.txt", b"This is a test file", content_type="text/plain"
        )

        self.test_data = {
            "name": "Test Template II",
            "sender": "info@example.com",
            "subject": f"Welcome <{PlaceHolderType.CANDIDATE_FIRST_NAME.value}>!",
            "template": f"Hi <{PlaceHolderType.CANDIDATE_FIRST_NAME.value}>, welcome to our company. Please contact us at <{PlaceHolderType.YOUR_COMPANY_NAME.value}>.",
            "placeholders": ",".join(
                [PlaceHolderType.CANDIDATE_FIRST_NAME.value, PlaceHolderType.YOUR_COMPANY_NAME.value]),
            "delays": 7,
            "bcc": ",".join(["bob@example.com", "joe@example.com"]),
            "cc": ",".join(["pitt@example.com"]),
            "personal": True,
            "attachments": [file_data],
        }
        self.email_template = EmailTemplate.objects.create(
            name="Test Template",
            sender="info@example.com",
            subject=f"Welcome <{PlaceHolderType.CANDIDATE_FULLNAME.value}>!",
            template=f"Hi <{PlaceHolderType.CANDIDATE_FULLNAME.value}>, welcome to our company. Please contact us at <{PlaceHolderType.YOUR_COMPANY_NAME.value}>.",
            placeholders=[PlaceHolderType.CANDIDATE_FULLNAME.value, PlaceHolderType.YOUR_COMPANY_NAME.value],
            delays=2,
            bcc=["H0c5e@example.com"],
            cc=["pitt@example.com"],
            personal=True,
            is_html=False,
            created_by=self.business_user
        )

    def test_update_email_template(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = self.test_data
        response = self.client.post(self.url(self.email_template.uid), data=data,
                                   headers=headers, format="multipart/form-data"
                                   )
        self.assertEqual(response.status_code, 200)
        template = EmailTemplate.objects.first()
        self.assertEqual(template.delays, data["delays"])
        self.assertEqual(template.personal, data["personal"])
        self.assertEqual(template.sender, data["sender"])
        self.assertEqual(template.subject, data["subject"])
        self.assertEqual(template.template, data["template"])
        self.assertEqual(template.name, data["name"])


    def test_for_invalid_subject_placeholder(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        self.test_data["subject"] = "hello <candidate>!"
        response = self.client.post(self.url(self.email_template.uid), self.test_data,
                                   headers=headers, format="multipart/form-data")
        logging.critical(response.content)
        logging.critical(response.json())
        self.assertEqual(response.status_code, 400)



    def test_for_invalid_subject_placeholder_format(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        self.test_data["subject"] = f"hello <<{PlaceHolderType.CANDIDATE_FULLNAME.value}>>!"
        response = self.client.post(self.url(self.email_template.uid), self.test_data,
                                   headers=headers, format="multipart/form-data")

        self.assertEqual(response.status_code, 400)


    def test_update_template_with_same_name(self):
        EmailTemplateFactory.create(name="Test Template 2", created_by=self.business_user, personal=True)
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = {
            "name": "Test Template 2",
            "personal": True
        }
        self.test_data.update(data)
        response = self.client.post(self.url(self.email_template.uid), self.test_data,
                                    headers=headers, format="multipart/form-data")

        self.assertEqual(response.status_code, 400)

    def test_update_template_by_team_member_business_user(self):
        business_user = BusinessUserFactory.create(role=BusinessUserRoleType.TEAM_MEMBER.value)
        headers = {"authorization": f"bearer {business_user.user.token}"}
        data = {
            "name": "Test Template 3"
        }
        self.test_data.update(data)
        response = self.client.post(self.url(self.email_template.uid), self.test_data,
                                    headers=headers, format="multipart/form-data")

        self.assertEqual(response.status_code, 403)

    def test_update_template_by_admin_business_user(self):
        business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)
        headers = {"authorization": f"bearer {business_user.user.token}"}
        data = {
            "name": "Test Template 3"
        }
        self.test_data.update(data)
        response = self.client.post(self.url(self.email_template.uid), self.test_data,
                                    headers=headers, format="multipart/form-data")

        self.assertEqual(response.status_code, 200)


class RetrieveEmailTemplateTest(TestCase):
    def setUp(self):
        self.client = self.client
        self.client = TestClient(router)
        self.url = lambda uid : f"email-templates/{uid}"
        self.business_user = BusinessUserFactory.create()
        templates = EmailTemplateFactory.create_batch(5, created_by=self.business_user)
        for template in templates:
            EmailTemplateAttachment.objects.create(email_template=template,
                                                   file=SimpleUploadedFile(
                                                       "test_file.txt", b"This is a test file", content_type="text/plain"
                                                   ))


    def test_retrieve_email_template(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        uid = EmailTemplate.objects.first().uid
        response = self.client.get(self.url(uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["uid"], str(uid))
        self.assertEqual(len(response.json()["attachments"]), 1)
        self.assertIn("name", response.json()["attachments"][0])
        print(response.json()["attachments"])

    def test_retrieve_email_template_by_another_business(self):
        template = EmailTemplateFactory.create()
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        uid = template.uid
        response = self.client.get(self.url(uid), headers=headers)
        self.assertEqual(response.status_code, 404)

class EmailTemplateListTest(TestCase):
    def setUp(self):
        self.client = self.client
        self.client = TestClient(router)
        self.url = "email-templates"
        self.business_user = BusinessUserFactory.create()
        EmailTemplateFactory.create_batch(5, created_by=self.business_user)

    def test_email_template_list(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)


class CreateWorkflowTest(TestCase):
    def setUp(self):
        self.client = self.client
        self.client = TestClient(router)
        self.url = "workflows/stages"
        self.business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)

    def test_create_workflow_stage(self):
        email_template = EmailTemplateFactory.create(created_by=self.business_user, personal=False)
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = {
            "name": "Test Workflow",
            "phase": PhaseType.ONBOARDING.value,
            "email_template": email_template.uid,
            "is_active": True
        }
        response = self.client.post(self.url, json=data,
                                    headers=headers)
        self.assertEqual(response.status_code, 201)
        data = {
            "name": "Test Workflow2",
            "phase": PhaseType.INTERVIEW.value,
            "email_template": email_template.uid,
            "is_active": True
        }
        response = self.client.post(self.url, json=data,
                                    headers=headers)
        self.assertEqual(response.status_code, 201)
        workflow = WorkFlowStage.objects.last()
        self.assertEqual(WorkFlowStage.objects.count(), 5)
        self.assertEqual(workflow.name, data["name"])

    def test_create_workflow_stage_with_same_name(self):
        email_template = EmailTemplateFactory.create(created_by=self.business_user, personal=True)
        WorkflowStageFactory.create(name="Test Workflow", phase=PhaseType.HIRED.value, created_by=self.business_user)
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = {
            "name": "Hired",
            "phase": PhaseType.HIRED.value,
            "email_template": email_template.uid,
            "is_active": True
        }
        response = self.client.post(self.url, json=data,
                                    headers=headers)
        self.assertEqual(response.status_code, 400)

class UpdateWorkflowTest(TestCase):
    def setUp(self):
        self.client = self.client
        self.client = TestClient(router)
        self.url = lambda uid : f"workflows/stages/{uid}"
        self.business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)
        email_template = EmailTemplateFactory.create(created_by=self.business_user, personal=False)
        self.workflow_stage = WorkflowStageFactory.create(created_by=self.business_user, is_active=True,
                                                       email_template=email_template,
                                                          phase=PhaseType.INTERVIEW.value)

    def test_update_workflow_stage(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = {
            "name": "Test Workflow II",
            "is_active": False
        }
        response = self.client.patch(self.url(self.workflow_stage.uid), json=data,
                                     headers=headers)
        self.assertEqual(response.status_code, 200)
        workflow = WorkFlowStage.objects.last()
        self.assertEqual(workflow.name, str(data["name"]))
        self.assertEqual(workflow.is_active, data["is_active"])

    def test_update_workflow_stage_with_same_name(self):
        WorkflowStageFactory.create(name="Test Workflow II", phase=self.workflow_stage.phase,
                                    created_by=self.business_user)
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = {
            "name": "Test Workflow II"
        }
        response = self.client.patch(self.url(self.workflow_stage.uid), json=data,
                                     headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_update_workflow_stage_by_another_business(self):
        business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)
        headers = {"authorization": f"bearer {business_user.user.token}"}
        data = {
            "name": "Test Workflow II"
        }
        response = self.client.patch(self.url(self.workflow_stage.uid), json=data,
                                     headers=headers)
        self.assertEqual(response.status_code, 404)


    def test_update_workflow_stage_by_team_member(self):
        business_user = BusinessUserFactory.create(role=BusinessUserRoleType.TEAM_MEMBER.value,
                                                   business=self.workflow_stage.created_by.business)
        headers = {"authorization": f"bearer {business_user.user.token}"}
        data = {
            "name": "Test Workflow II"
        }
        response = self.client.patch(self.url(self.workflow_stage.uid), json=data,
                                     headers=headers)
        self.assertEqual(response.status_code, 403)


    def test_deactivate_workflow_stage(self):
        self.workflow_stage.is_active = True
        self.workflow_stage.save()
        JobApplicationFactory.create(stage=self.workflow_stage)

        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = {
            "is_active": False
        }
        response = self.client.patch(self.url(self.workflow_stage.uid), json=data,
                                     headers=headers)
        self.assertEqual(response.status_code, 400)

class RetrieveWorkflowStagesTest(TestCase):
    def setUp(self):
        self.client = self.client
        self.client = TestClient(router)
        self.url = "workflows/stages"
        self.business_user = BusinessUserFactory.create()
        WorkflowStageFactory.create_batch(5, created_by=self.business_user)

    def test_retrieve_workflow_stages(self):
        first_stage = WorkFlowStage.objects.first()
        first_stage.phase = PhaseType.HIRED.value
        first_stage.save()
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        phases = [item["phase"] for item in data]
        self.assertEqual(phases, list(PhaseType.values()))
        first_data = list(filter(lambda item: item["phase"] == PhaseType.HIRED.value, data))[0]
        self.assertIn("phase", first_data)
        self.assertIn("stages", first_data)
        self.assertGreaterEqual(len(first_data["stages"]), 1)

class DeleteAttachmentFromEmailTemplateTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = lambda uid : f"email-templates/{uid}/attachments"
        self.business_user = BusinessUserFactory.create()
        self.email_template = EmailTemplateFactory.create(created_by=self.business_user)
        file_data = SimpleUploadedFile(
                       "test_file.txt", b"This is a test file", content_type="text/plain"
                     )
        self.attachment = EmailTemplateAttachment.objects.create(email_template=self.email_template,
                                                                 file=file_data)


    def test_delete_attachment_from_email_template(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        response = self.client.delete(self.url(self.email_template.uid),
                                               json=[self.attachment.uid],
                                      headers=headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(EmailTemplateAttachment.objects.filter(email_template=self.email_template).count(), 0)

    def test_delete_attachment_from_email_template_by_another_business(self):
        business_user = BusinessUserFactory.create()
        headers = {"authorization": f"bearer {business_user.user.token}"}
        response = self.client.delete(self.url(self.email_template.uid),
                                               json=[self.attachment.uid],
                                      headers=headers)
        self.assertEqual(response.status_code, 404)


class ReArrangeWorkflowTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "workflows/re-arrange-stages"
        self.business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)
        self.stage1 = WorkflowStageFactory.create(created_by=self.business_user, phase=PhaseType.HIRED.value, order=1)
        self.stage2 = WorkflowStageFactory.create(created_by=self.business_user, phase=PhaseType.HIRED.value, order=2)

    def test_successful_rearrangement(self):
        headers = {"authorization": f"bearer {self.business_user.user.token}"}
        data = [{"stage_uids": [str(self.stage2.uid), str(self.stage1.uid)], "phase": PhaseType.HIRED.value}]
        response = self.client.patch(self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "workflow stages have been updated successfully")

        self.stage1.refresh_from_db()
        self.stage2.refresh_from_db()
        self.assertEqual(self.stage1.order, 1)
        self.assertEqual(self.stage2.order, 0)

    def test_unauthorized_access(self):
        """Test access without authentication"""
        data = [{"stage_uids": [str(self.stage1.uid)], "phase": PhaseType.HIRED.value}]
        response = self.client.patch(self.url, json=data)
        self.assertEqual(response.status_code, 401)




class BulkDeleteEmailTemplatesTest(TestCase):
    def setUp(self):
        self.url = "email-templates"
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)
        templates = EmailTemplateFactory.create_batch(5, created_by=self.business_user)
        self.test_data = [
            str(template.uid) for template in templates
        ]

    def test_bulk_delete_templates(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 204)

        self.assertEqual(EmailTemplate.objects.filter(created_by=self.business_user).count(), 0)

    def test_by_another_business_user(self):
        business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.delete(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 204)

        self.assertEqual(EmailTemplate.objects.filter(created_by=self.business_user).count(), 5)

    def test_bulk_delete_without_authorization(self):
        response = self.client.delete(self.url, json=self.test_data)
        self.assertEqual(response.status_code, 401)

    def test_bulk_delete_by_talent(self):
        talent_user = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent_user.user.token}"
        }
        response = self.client.delete(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 403)


class BulkDeleteWorkflowStageTest(TestCase):
    def setUp(self):
        self.url = "workflows/stages"
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)
        stages = WorkflowStageFactory.create_batch(5, created_by=self.business_user, is_active=False, phase=PhaseType.INTERVIEW.value)
        self.test_data = [
            str(stage.uid) for stage in stages
        ]

    def test_bulk_delete_by_business_user(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(WorkFlowStage.objects.filter(created_by=self.business_user).count(), 3)

    def test_when_one_stage_is_active(self):
        w = WorkFlowStage.objects.last()
        w.update(is_active=True)
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WorkFlowStage.objects.filter(created_by=self.business_user).count(), 8)

    def test_when_one_stage_has_job_applications(self):
        w = WorkFlowStage.objects.last()
        JobApplicationFactory.create(stage=w)
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WorkFlowStage.objects.filter(created_by=self.business_user).count(), 8)


    def test_by_another_business_user(self):
        business_user = BusinessUserFactory.create(role=BusinessUserRoleType.ADMIN.value)
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.delete(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(WorkFlowStage.objects.filter(created_by=self.business_user).count(), 8)

    def test_by_talent(self):
        talent = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent.user.token}"
        }
        response = self.client.delete(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(WorkFlowStage.objects.filter(created_by=self.business_user).count(), 8)




class MoveApplicantsAcrossStagesTest(TestCase):
    def setUp(self):
        self.url = "workflows/stages/move-applications"
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.previous_stage = WorkflowStageFactory.create(created_by=self.business_user, is_active=False)
        self.next_stage = WorkflowStageFactory.create(created_by=self.business_user, is_active=False)
        self.test_data = {
            "previous_stage_uid": str(self.previous_stage.uid),
            "next_stage_uid": str(self.next_stage.uid)
        }
        JobApplicationFactory.create_batch(5, stage=self.previous_stage)



    def test_by_business_user(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        self.assertEqual(JobApplication.objects.filter(stage=self.previous_stage).count(), 5)
        self.assertEqual(JobApplication.objects.filter(stage=self.next_stage).count(), 0)
        response = self.client.post(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.filter(stage=self.previous_stage).count(), 0)
        self.assertEqual(JobApplication.objects.filter(stage=self.next_stage).count(), 5)

    def test_by_another_business_user_in_another_company(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        self.assertEqual(JobApplication.objects.filter(stage=self.previous_stage).count(), 5)
        self.assertEqual(JobApplication.objects.filter(stage=self.next_stage).count(), 0)
        response = self.client.post(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(JobApplication.objects.filter(stage=self.previous_stage).count(), 5)
        self.assertEqual(JobApplication.objects.filter(stage=self.next_stage).count(), 0)

    def test_by_talent(self):
        talent = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent.user.token}"
        }
        self.assertEqual(JobApplication.objects.filter(stage=self.previous_stage).count(), 5)
        self.assertEqual(JobApplication.objects.filter(stage=self.next_stage).count(), 0)
        response = self.client.post(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(JobApplication.objects.filter(stage=self.previous_stage).count(), 5)
        self.assertEqual(JobApplication.objects.filter(stage=self.next_stage).count(), 0)