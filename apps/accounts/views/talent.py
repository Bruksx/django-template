import json
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from config.permissions import IsBusinessUser
from config.permissions import IsTalentUser
from django.db import transaction
from django.utils import timezone
from django_q.models import Schedule
from helpers.email.auth import send_verification_code
from helpers.utils import convert_base64_to_image_file, validate_password, delete_s3_item
from monkeypatches.q_cluster import async_task
from monkeypatches.response import Response
from ninja import Router, PatchDict, UploadedFile, File
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from services import meeting
from services.ai import parse_cv
from services.ai.schema import ParsedTalentProfileSchema

from accounts.enums import MeetingType
from accounts.enums import UserType, AuthType
from accounts.models import Talent, TalentAvailableDay, BannedAccount
from accounts.models import User, VerificationCode, Education, Experience
from accounts.schemas import common as common_schemas
from accounts.schemas import talent as talent_schemas
from auth.schema import OptionalLoginSchema
from auth.services import validate_login

router = Router(tags=["Account"])

@router.post("initiate-account-creation")
def initiate_account_creation(request, data: common_schemas.RegisterSchema):
    if BannedAccount.objects.filter(
            email__iexact=data.email,
            account_type=UserType.TALENT.value
    ).exists():
        raise HttpError(401, "This account has been banned")
    existing_user = User.objects.filter(email__iexact=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode(email=data.email)
    raw_code = verification_code.save()
    async_task(send_verification_code, email=data.email, code=raw_code, user="", company=None)
    return {
        "message": "verification mail sent!"
    }


@router.post("create-account", response={200:talent_schemas.LoggedInUserSchema})
@transaction.atomic
def create_account(request, data: talent_schemas.ValidateTalentOTPSchema):
    existing_user = User.objects.filter(email__iexact=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode.objects.filter(email__iexact=data.email).last()
    if not verification_code:
        raise HttpError(400, "Incorrect otp")
    is_correct = verification_code.verify_code(data.otp)
    if not is_correct:
        raise HttpError(400, "This OTP is invalid")
    validate_password(password=data.password)
    user = User.objects.create_user(first_name=data.first_name,
                                    last_name=data.last_name,
                                    email=data.email.lower().strip(),
                                    password=data.password,
                                    username=None,
                                    auth_mode=AuthType.EMAIL.value,
                               type=UserType.TALENT.value,
                               email_verified=True, is_active=True)
    talent = Talent.objects.create(
        user=user
    )
    Schedule.objects.create(
        func='helpers.email.accounts.send_incomplete_profile_reminder_email',
        schedule_type=Schedule.ONCE,
        next_run=talent.created_at + timedelta(days=1),
        kwargs=json.dumps({"emails": [user.email], "name": user.first_name})
    )
    return user

@router.get("profile", response=talent_schemas.TalentUserSchema, auth=JWTAuth())
def talent_profile(request):
    IsTalentUser.check(request)
    return request.user.talent

@router.delete("education/{education_uid}",
               response={204: None},
               auth=JWTAuth())
def delete_talent_education(request, education_uid:UUID):
    IsTalentUser.check(request)
    talent_user = request.user.talent
    education = talent_user.education_set.filter(uid=education_uid).first()
    if not education:
        raise HttpError(404, "This education does not exist")
    education.hard_delete()
    return Response(status=204, data=None)


@router.delete("experience/{experience_uid}",
               response={204: None}, auth=JWTAuth())
def delete_talent_experience(request, experience_uid:UUID):
    IsTalentUser.check(request)
    talent_user = request.user.talent
    experience = talent_user.experience_set.filter(uid=experience_uid).first()
    if not experience:
        raise HttpError(404, "This experience does not exist")
    experience.hard_delete()
    return Response(status=204, data=None)


@router.get("dashboard-report", response=talent_schemas.TalentDashboardReport, auth=JWTAuth(),
            tags=["Talent Dashboard"])
def talent_dashboard_report(request, start_date: date=None, end_date: date=None):
    IsTalentUser.check(request)
    if start_date and end_date:
        # if the range is inclusive
        end_date = end_date + timedelta(days=1)
        return Response(data=talent_schemas.TalentDashboardReport.from_orm(request.user.talent, context={
                "start_date": start_date,
                "end_date": end_date
            }))

    return Response(data=talent_schemas.TalentDashboardReport.from_orm(request.user.talent))

@router.get("dashboard-charts", response=talent_schemas.TalentDashboardChartsSchema, auth=JWTAuth(),
            tags=["Talent Dashboard"])
def talent_dashboard_chart(request):
    IsTalentUser.check(request)
    return request.user.talent.dashboard_charts()

@router.patch("profile", auth=JWTAuth(), response=talent_schemas.TalentUserListSchema)
@transaction.atomic
def update_talent_profile(request, data: PatchDict[talent_schemas.UpdateTalentProfileSchema2]):
    IsTalentUser.check(request)
    talent_user: Talent = request.user.talent
    if "gender" in data:
        data["gender"] = data["gender"].value if type(data["gender"]) is not str else data["gender"]


    if "work_models" in data:
        wm_func = lambda x: x.value if type(x) is not str else x
        if data["work_models"] is not None:
            data["work_models"] = list(map(wm_func, data["work_models"]))


    if "preferred_communication" in data:
        
        data["preferred_communication"] = data["preferred_communication"].value if type(data["preferred_communication"]) is not str else data["preferred_communication"]
    if "notice_period_type" in data:
        data["notice_period_type"] = data["notice_period_type"].value if type(data["notice_period_type"]) is not str else data["notice_period_type"]
    if "notice_period" in data:
        data["notice_period"] = data["notice_period"] if type(data["notice_period"]) is not str else int(data["notice_period"]) if str(data["notice_period"]).isdigit() else None


    user = request.user
    user_data = dict()
    if "first_name" in data:
        user_data["first_name"] = data.pop("first_name", None)
    if "last_name" in data:
        user_data["last_name"] = data.pop("last_name", None)
    if "gender" in data:
        user_data["gender"] = data.pop("gender", None)
    if "photo" in data:
        data["photo"] = convert_base64_to_image_file(data["photo"])
    if "phone_number" in data:
        user_data["phone_number"] = data.pop("phone_number")
    if "phone_code" in data:
        user_data["phone_code"] = data.pop("phone_code")
    if "skills" in data:
        if data["skills"]:
            talent_user.skills.set(data.pop("skills"))
        else:
            data.pop("skills", None)
            talent_user.skills.clear()
    if "business_models" in data:
        if data["business_models"]:
            talent_user.business_models.set(data.pop("business_models"))
        else:
            data.pop("business_models", None)
            talent_user.business_models.clear()
    if "experience_history" in data and data["experience_history"]:
        uids = list()
        for experience in data.pop("experience_history"):
            experience_uid = experience.pop("uid", None)
            currently_works = experience.get("currently_works_here", False)
            start_date = experience.get("start_date", None)
            end_date = experience.get("end_date", None)
            if experience.get("salary_type"):
                experience["salary_type"] = experience["salary_type"].value if type(experience["salary_type"]) is not str else experience[
                    "salary_type"]

            if experience.get("salary_bonus_type"):
                experience["salary_bonus_type"] = experience["salary_bonus_type"].value if type(
                    experience["salary_bonus_type"]) is not str else experience["salary_bonus_type"]

            if not start_date:
                raise HttpError(400, "Experience start date is required")
            if currently_works is True:
                experience["end_date"] = None
            else:
                if not end_date:
                    raise HttpError(400, "Experience end date is required if not currently working here")
                if end_date < start_date:
                    raise HttpError(400, "Experience end date cannot be before start date")
                if end_date > timezone.now().date():
                    raise HttpError(400, "Experience end date cannot be in the future")

            if experience_uid:
                talent_user.experience_set.filter(uid=experience_uid).update(**experience)
                uids.append(experience_uid)
            else:
                experience = Experience.objects.create(**experience, talent=talent_user)
                uids.append(experience.uid)
        talent_user.experience_set.exclude(uid__in=uids).hard_delete()
    if "education_history" in data and data["education_history"]:
        uids = list()
        for education in data.pop("education_history"):
            edu_uid = education.pop("uid", None)
            if edu_uid:
                talent_user.education_set.filter(uid=edu_uid).update(**education)
                uids.append(edu_uid)
            else:
                education  = Education.objects.create(**education, talent=talent_user)
                uids.append(education.uid)
        talent_user.education_set.exclude(uid__in=uids).hard_delete()
    if "additional_languages" in data:
        additional_languages = data.pop("additional_languages", list())
        if additional_languages:
            talent_user.additional_languages.set(additional_languages)
        else:
            talent_user.additional_languages.clear()
    if "employment_types" in data:
        employment_types = data.pop("employment_types", list())
        if employment_types:
            talent_user.employment_types.set(employment_types)
        else:
            talent_user.employment_types.clear()

    if "availability" in data and data["availability"]:
        for available_day in data.pop("availability"):
            available_day["day"] = available_day["day"].value
            uid = available_day.pop("uid", None)
            active = available_day.pop("active", True)
            if uid and not active:
                talent_user.talentavailableday_set.filter(uid=uid).delete()
            elif uid and active:
                talent_user.talentavailableday_set.filter(uid=uid).update(**available_day)
            elif not uid:
                day = available_day['day']
                if not talent_user.talentavailableday_set.filter(day=day).exists():
                    TalentAvailableDay.objects.create(**available_day, talent=talent_user)
                    
    data.pop("skills", None)
    data.pop("business_models", None)
    user.update(**user_data)
    return talent_user.update(**data)
    

@router.patch("change-password", auth=JWTAuth())
def change_talent_password(request, data: talent_schemas.TalentChangePasswordSchema):
    IsTalentUser.check(request)
    user = request.user
    if not user.check_password(data.old_password):
        raise HttpError(400, "Incorrect Password")
    validate_password(password=data.new_password)
    user.set_password(data.new_password)
    user.save()
    return Response(status=200, data={"message": "Password changed successfully"})

@router.post("cv", auth=JWTAuth(), response=ParsedTalentProfileSchema)
def upload_talent_cv(request, file: Optional[UploadedFile] = File(None), parse="false"):
    IsTalentUser.check(request)
    talent_user: Talent = request.user.talent
    if not file:
        if talent_user.cv:
            delete_s3_item(talent_user.cv.url)
        talent_user.update(cv=None)
        return Response(status=200, data={"message": "CV cleared successfully"})
    if file.name.split(".")[-1] != "pdf":
        raise HttpError(400, "This file type is not supported. Only PDF files")
    talent_user.update(cv=file)
    if parse.lower() == "true":
        if not talent_user.cv:
           raise HttpError(400, "No CV available for parsing")

        parsed_data = parse_cv(talent_user.cv.url)
        return Response(parsed_data)
    return Response(status=200, data={"message": "CV uploaded successfully"})

@router.post("profile-pic", auth=JWTAuth())
def upload_talent_profile_picture(request, file: Optional[UploadedFile] = File(None)):
    IsTalentUser.check(request)
    talent_user = request.user.talent
    if not file:
        if talent_user.photo_url:
            async_task(delete_s3_item, talent_user.photo_url)
        async_task(talent_user.update, photo=None)
        return Response(status=200, data={"message": "Profile picture cleared successfully"})
    extension = str(file.name.split(".")[-1]).lower()
    if extension not in ["jpg", "jpeg", "png"]:
        raise HttpError(400, "This file type is not supported. Only JPG/JPEG/PNG files")
    async_task(talent_user.update, photo=file)
    return Response(status=200, data={"message": "Profile picture uploaded successfully"})


@router.get("{talent_uid}", response=talent_schemas.TalentUserSchema, auth=JWTAuth())
def talent_details(request, talent_uid:UUID):
    IsBusinessUser.check(request)
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "This talent does not exist")
    if not talent.viewers.filter(id=request.user.id).exists():
        talent.viewers.add(request.user)
        talent.save()
    return talent


@router.post("schedule-meeting", auth=JWTAuth(), response=talent_schemas.MeetingResponse)
def schedule_meeting(request, data: talent_schemas.ScheduleMeetingSchema):
    IsBusinessUser.check(request)
    meeting_response = None
    if data.meeting_type == MeetingType.GOOGLE_MEET:
        meeting_response = meeting.google_meet.create_meeting(data.meeting, data.meeting.google_meet_specifi.get("access_token"))
    elif data.meeting_type == MeetingType.ZOOM:
        meeting_response = meeting.zoom.create_meeting(data.meeting)
    elif data.meeting_type == MeetingType.MICROSOFT_TEAMS:
        meeting_response = meeting.teams.create_meeting(data.meeting)
    if not meeting_response:
        raise HttpError(400, "Meeting could not be scheduled")

    return meeting_response

@router.delete("", response={204: None})
@transaction.atomic
def delete_account(request, data: OptionalLoginSchema = {}):
    #optionally requires auth
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header:
        _, _, token = auth_header.partition(" ")
    if token:
        user = JWTAuth().authenticate(request, token)
    else:
        user: User = User.objects.filter(email=data.email).first()
        validate_login(user)
        if not user.check_password(data.password):
            raise HttpError(400, "Incorrect Password")
    user.delete_account()
    return Response(status=204, data={"message": "Account deleted successfully"})