from typing import List
from uuid import UUID

from accounts.enums import BusinessUserRoleType
from django.db import transaction
from django.db.models import Q
from jobs.enums import PhaseType
from jobs.models import JobApplication
from ninja import Router, Form, PatchDict, UploadedFile
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from settings.models import EmailTemplate, EmailTemplateAttachment, WorkFlowStage
from settings.schemas import CreateEmailTemplateSchema, EmailTemplateListSchema, EmailTemplateDetailSchema, \
    MutateWorkFlowStageSchema, WorkFlowStageSchema, PhaseWorkFlowStageSchema, RearrangeWorkflowStageSchema, \
    MoveApplicationToStageFromStageSchema, UpdateEmailTemplateSchema

from config.permissions import IsBusinessUser, IsBusinessOwnerOrAdmin
from monkeypatches.response import Response

router = Router(tags=["Settings"])

@router.post("email-templates", auth=JWTAuth())
@transaction.atomic
def create_email_template(request, body:CreateEmailTemplateSchema=Form(), attachments:List[UploadedFile]=None):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    if EmailTemplate.objects.filter(created_by__business=business_user.business, name__iexact=body.name,
                                    personal=body.personal).exists():
        raise HttpError(400, "An email template with this name already exists")
    data = body.__dict__.copy()
    CreateEmailTemplateSchema.is_valid(data=data)
    template = EmailTemplate.objects.create(**data, created_by=business_user)
    if attachments:
        EmailTemplateAttachment.objects.bulk_create(
            [EmailTemplateAttachment(
                email_template=template,
                file=attachment
            ) for attachment in attachments]
        )
    return Response(status=201, data={"message": "email template has been created successfully"})

@router.post("email-templates/{template_uid}", auth=JWTAuth())
@transaction.atomic
def update_email_template(request, template_uid:UUID, body:UpdateEmailTemplateSchema=Form(), attachments:List[UploadedFile]=None):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    template = EmailTemplate.objects.filter(uid=template_uid).first()
    if not template:
        raise HttpError(404, "This email template does not exist")
    data = body.__dict__.copy()
    personal = data.get("personal", template.personal)
    if "name" in data and EmailTemplate.objects.filter(created_by__business=business_user.business,
        personal=personal, name__iexact=data["name"]).exclude(uid=template_uid).exists():
        raise HttpError(400, "An email template with this name already exists")
    if business_user.role not in [BusinessUserRoleType.OWNER.value, BusinessUserRoleType.ADMIN.value, BusinessUserRoleType.TALENT_MANAGER.value] and \
        template.created_by != business_user:
        raise HttpError(403, "You do not have permission to update this email template")
    UpdateEmailTemplateSchema.is_valid(data=data, instance=template)
    template.update(**data)
    if attachments:
        EmailTemplateAttachment.objects.bulk_create(
            [EmailTemplateAttachment(
                email_template=template,
                file=attachment
            ) for attachment in attachments]
        )
    return Response(status=200, data={"message": "email template has been updated successfully"})


@router.delete("email-templates/{template_uid}/attachments", auth=JWTAuth())
@transaction.atomic
def remove_attachments_from_email_template(request, template_uid:UUID, data: List[UUID]):
    IsBusinessUser.check(request)
    template = EmailTemplate.objects.filter(uid=template_uid, created_by__business=request.user.businessuser.business).first()
    if not template:
        raise HttpError(404, "This email template does not exist")
    attachments = EmailTemplateAttachment.objects.filter(email_template=template, uid__in=data)
    for attachment in attachments:
        attachment.hard_delete()
    return Response(status=204, data={"message": "attachments have been removed successfully"})

@router.get("email-templates", auth=JWTAuth(), response=List[EmailTemplateListSchema])
def retrieve_all_email_templates(request, personal:bool=None):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    queryset = EmailTemplate.objects.filter(created_by__business=business_user.business).exclude(Q(
        personal=True
    ) & ~Q(created_by=business_user)
    )
    if personal is not None:
        queryset = queryset.filter(personal=personal)
    request.context = {"business_user": business_user}
    return queryset.order_by("name")

@router.get("email-templates/{template_uid}", auth=JWTAuth(), response=EmailTemplateDetailSchema)
def retrieve_email_template(request, template_uid:UUID):
    IsBusinessUser.check(request)
    request.context = {"business_user": request.user.businessuser}
    business = request.user.businessuser.business
    template = EmailTemplate.objects.filter(uid=template_uid, created_by__business=business).first()
    if not template:
        raise HttpError(404, "This email template does not exist")
    return template

@router.delete("email-templates", auth=JWTAuth())
def bulk_delete_email_templates(request, template_uids:List[UUID]):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    query = dict(uid__in=template_uids)
    if business_user.role not in [BusinessUserRoleType.OWNER.value, BusinessUserRoleType.ADMIN.value]:
        query["created_by"] = business_user
    else:
        query["created_by__business"] = business_user.business

    templates = EmailTemplate.objects.filter(**query)
    for template in templates:
        if template.workflowstage_set.count() > 0:
            raise HttpError(400, f'Some workflow stages are using this email template: "{template.name}"')
    templates.delete()
    return Response(status=204, data={"message": "email templates have been deleted successfully"})

@router.delete("workflows/stages", auth=JWTAuth())
def bulk_delete_workflow_stage(request, stage_uids:List[UUID]):
    IsBusinessOwnerOrAdmin.check(request)
    stages = WorkFlowStage.objects.filter(uid__in=stage_uids, created_by__business=request.user.businessuser.business)
    for stage in stages:
        if stage.is_active is True:
            raise HttpError(400, f"This workflow stage '{stage.name}' is still active")
        if stage.jobapplication_set.count() > 0:
            raise HttpError(400, f"This workflow stage '{stage.name}' has job applications")
        if stage.phase in (PhaseType.NEW.value, PhaseType.HIRED.value, PhaseType.REJECTED.value):
            raise HttpError(400, f"This workflow stage '{stage.name}' is a default stage ")
    stages.delete()
    return Response(status=204, data={"message": "workflow stage has been deleted successfully"})

@router.post("workflows/stages/move-applications", auth=JWTAuth(), response=EmailTemplateDetailSchema)
@transaction.atomic
def move_applicants_across_stages(request, data: MoveApplicationToStageFromStageSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    previous_stage = WorkFlowStage.objects.filter(uid=data.previous_stage_uid, created_by__business=business_user.business).first()
    if not previous_stage:
        raise HttpError(404, f"The selected previous stage does not exist")
    next_stage = WorkFlowStage.objects.filter(uid=data.next_stage_uid, created_by__business=business_user.business).first()
    if not next_stage:
        raise HttpError(404, "This selected next stage does not exist")
    JobApplication.objects.filter(stage=previous_stage).update(stage=next_stage)
    return Response(status=200, data={"message": "applicants have been moved successfully"})


@router.post("workflows/stages", auth=JWTAuth())
@transaction.atomic
def create_workflow_stage(request, data: MutateWorkFlowStageSchema):
    IsBusinessOwnerOrAdmin.check(request)
    business_user = request.user.businessuser
    if WorkFlowStage.objects.filter(created_by__business=business_user.business, name__iexact=data.name,
                                    phase=data.phase.value).exists():
        raise HttpError(400, "A workflow stage with this name in this phase already exists")
    if data.phase in [PhaseType.NEW, PhaseType.REJECTED, PhaseType.HIRED]:
        if WorkFlowStage.objects.filter(created_by__business=business_user.business, phase=data.phase.value).exists():
            raise HttpError(400, "You cannot create more than one workflow stage in this phase")
    if data.email_template and EmailTemplate.objects.filter(uid=data.email_template, personal=True).exists():
        raise HttpError(400, "Personal templates are not used for stages")

    wrk_flow_data = data.__dict__.copy()
    wrk_flow_data["phase"] = wrk_flow_data["phase"].value
    wrk_flow_data["phase_order"] = PhaseType.values().index(wrk_flow_data["phase"])
    WorkFlowStage.objects.create(**wrk_flow_data, created_by=business_user)
    return Response(status=201, data={"message": "workflow stage has been created successfully"})

@router.patch("workflows/stages/{stage_uid}", auth=JWTAuth())
@transaction.atomic
def update_workflow_stage(request, stage_uid:UUID, data:PatchDict[MutateWorkFlowStageSchema]):
    IsBusinessOwnerOrAdmin.check(request)
    business_user = request.user.businessuser
    stage = WorkFlowStage.objects.filter(uid=stage_uid, created_by__business=business_user.business).first()
    if not stage:
        raise HttpError(404, "This workflow stage does not exist")
    if business_user.role not in [BusinessUserRoleType.OWNER.value, BusinessUserRoleType.ADMIN.value] and \
        stage.created_by != business_user:
        raise HttpError(403, "You do not have permission to update this workflow stage")
    if "phase" in data:
        data["phase"] = data["phase"].value
        data["phase_order"] = PhaseType.values().index(data["phase"])
        if stage.phase in [PhaseType.NEW.value, PhaseType.REJECTED.value, PhaseType.HIRED.value] and stage.phase != data["phase"]:
            raise HttpError(400, "You cannot change the phase of this workflow stage")
        if data["phase"] in [PhaseType.NEW.value, PhaseType.REJECTED.value, PhaseType.HIRED.value] and stage.phase != data["phase"]:
            raise HttpError(400, "You cannot add a workflow stage in this phase")
    if "name" in data:
        if stage.phase in [PhaseType.NEW.value, PhaseType.REJECTED.value, PhaseType.HIRED.value] and str(stage.name).lower() != str(data["name"]).lower():
            raise HttpError(400, "You cannot change the name of this workflow stage")

    if data.get("email_template") and EmailTemplate.objects.filter(uid=data.get("email_template"), personal=True).exists():
        raise HttpError(400, "Personal templates are not used for stages")

    phase = data.get("phase", stage.phase)
    if "name" in data and  WorkFlowStage.objects.filter(created_by__business=business_user.business, name__iexact=data["name"],
                                    phase=phase).exclude(id=stage.id).exists():
        raise HttpError(400, "A workflow stage with this name in this phase already exists")
    # if is_active is set to false, check if this stage can be deactivated
    if "is_active" in data and stage.is_active is True and data["is_active"] is False and stage.can_be_deactivated() is False:
        raise HttpError(400, "This workflow stage cannot be deactivated")

    stage.update(**data)
    return Response(status=200, data={"message": "workflow stage has been updated successfully"})


@router.get("workflows/stages", auth=JWTAuth(), response=List[PhaseWorkFlowStageSchema])
def retrieve_all_workflow_stages(request):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    phases = PhaseType.values()
    workflows = WorkFlowStage.objects.filter(created_by__business=business_user.business)
    return [
        dict(phase=phase,
             stages=[WorkFlowStageSchema.from_orm(stage).dict() for stage in workflows.filter(phase=phase).order_by("order")]
             )
        for phase in phases
        ]

@router.patch("workflows/re-arrange-stages", auth=JWTAuth())
@transaction.atomic
def re_arrange_workflows(request, data:List[RearrangeWorkflowStageSchema]):
    IsBusinessOwnerOrAdmin.check(request)
    business_user = request.user.businessuser
    for arrangement in data:
        for stage in arrangement.stage_uids:
            WorkFlowStage.objects.filter(uid=stage, created_by__business=business_user.business,
                                         phase=arrangement.phase.value).update(order=arrangement.stage_uids.index(stage))
    return Response(status=200, data={"message": "workflow stages have been updated successfully"})