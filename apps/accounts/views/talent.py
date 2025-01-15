from datetime import date, timedelta
from typing import List
from uuid import UUID

from apps.accounts.enums import MeetingType
from config.permissions import IsBusinessUser
from config.permissions import IsTalentUser
from django.db import transaction
from django.shortcuts import get_object_or_404
from helpers.email.auth import send_verification_code
from helpers.utils import convert_base64_to_image_file, validate_password
from monkeypatches.q_cluster import async_task
from ninja import Router, PatchDict, UploadedFile
from ninja.errors import HttpError
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth
from services import meeting

from accounts.enums import UserType, AuthType
from accounts.models import Talent, TalentAvailableDay
from accounts.models import User, VerificationCode, Education, Experience
from accounts.schemas import common as common_schemas
from accounts.schemas import talent as talent_schemas
from accounts.services import download_talent_cv

router = Router(tags=["Account"])

@router.post("initiate-account-creation")
def initiate_account_creation(request, data: common_schemas.RegisterSchema):
    if User.deleted_objects.filter(email__iexact=data.email).exists():
        raise HttpError(400, "Reach out to get your account restored")

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
    existing_user = User.objects.filter(email=data.email).exists()
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
                                    email=data.email.lower(),
                                    password=data.password,
                                    username=None,
                                    auth_mode=AuthType.EMAIL.value,
                               type=UserType.TALENT.value,
                               email_verified=True, is_active=True)
    Talent.objects.create(
        user=user
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
    education.delete()
    return Response(status=204, data=None)


@router.delete("experience/{experience_uid}",
               response={204: None}, auth=JWTAuth())
def delete_talent_experience(request, experience_uid:UUID):
    IsTalentUser.check(request)
    talent_user = request.user.talent
    experience = talent_user.experience_set.filter(uid=experience_uid).first()
    if not experience:
        raise HttpError(404, "This experience does not exist")
    experience.delete()
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

@router.get("applications-chart", response=List[talent_schemas.MonthlyChartSchema], auth=JWTAuth(),
            tags=["Talent Dashboard"])
def talent_applications_chart(request):
    IsTalentUser.check(request)
    return request.user.talent.applications_made_chart()


@router.get("interviews-chart", response=List[talent_schemas.MonthlyChartSchema],
            tags=["Talent Dashboard"], auth=JWTAuth())
def talent_interview_chart(request):
    IsTalentUser.check(request)
    return request.user.talent.interviews_chart()


@router.patch("profile", auth=JWTAuth())
@transaction.atomic
def update_talent_profile(request, data: PatchDict[talent_schemas.UpdateTalentProfileSchema2]):
    IsTalentUser.check(request)
    talent_user = request.user.talent
    if "gender" in data:
        data["gender"] = data["gender"].value
    if "preferred_communication" in data:
        data["preferred_communication"] = data["preferred_communication"].value
    if "notice_period_type" in data:
        data["notice_period_type"] = data["notice_period_type"].value
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
    if "skills" in data and data["skills"]:
        talent_user.skills.set(data.pop("skills"))
    if "business_models" in data and data["business_models"]:
        talent_user.business_models.set(data.pop("business_models"))
    if "experience_history" in data and data["experience_history"]:
        for experience in data.pop("experience_history"):
            experience_uid = experience.pop("uid", None)
            if experience_uid:
                if not talent_user.experience_set.filter(uid=experience_uid).exists():
                    continue
                talent_user.experience_set.filter(uid=experience_uid).update(**experience)
            else:
                Experience(**experience, talent=talent_user).save()
    if "education_history" in data and data["education_history"]:
        for education in data.pop("education_history"):
            edu_uid = education.pop("uid", None)
            if edu_uid:
                if not talent_user.education_set.filter(uid=edu_uid).exists():
                    continue
                talent_user.education_set.filter(uid=edu_uid).update(**education)
            else:
                Education(**education, talent=talent_user).save()
    if "additional_languages" in data and data["additional_languages"]:
        additional_languages = data.pop("additional_languages")
        talent_user.additional_languages.set(additional_languages)
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
    user.update(**user_data)
    talent_user.update(**data)
    return Response(status=200, data={"message": "Profile updated successfully"})

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

@router.post("cv", auth=JWTAuth())
def upload_talent_cv(request, file: UploadedFile):
    IsTalentUser.check(request)
    talent_user = request.user.talent
    if file.name.split(".")[-1] != "pdf":
        raise HttpError(400, "This file type is not supported. Only PDF files")
    talent_user.update(cv=file)
    return Response(status=200, data={"message": "CV uploaded successfully"})

@router.get("resume", auth=JWTAuth())
def download_talent_system_generated_cv(request):
    IsTalentUser.check(request)
    talent_user = request.user.talent
    return download_talent_cv(request, talent_user)

@router.post("profile-pic", auth=JWTAuth())
def upload_talent_profile_picture(request, file: UploadedFile):
    IsTalentUser.check(request)
    talent_user = request.user.talent
    extension = file.name.split(".")[-1]
    if extension not in ["jpg", "jpeg", "png"]:
        raise HttpError(400, "This file type is not supported. Only JPG/JPEG/PNG files")
    talent_user.update(photo=file)
    return Response(status=200, data={"message": "Profile picture uploaded successfully"})




@router.get("{talent_uid}", response=talent_schemas.TalentUserSchema, auth=JWTAuth())
def talent_details(request, talent_uid:UUID):
    IsBusinessUser.check(request)
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "This talent does not exist")
    return talent


@router.get("{talent_uid}/resume", auth=JWTAuth())
def download_talent_system_resume(request, talent_uid:UUID):
    IsBusinessUser.check(request)
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "This talent does not exist")
    return download_talent_cv(request, talent)


@router.post("{talent_uid}/schedule-meeting", auth=JWTAuth(), response=talent_schemas.MeetingResponse)
def schedule_meeting(request, talent_uid, data: talent_schemas.ScheduleMeetingSchema):
    IsBusinessUser.check(request)
    meeting_response = None
    talent = get_object_or_404(Talent, uid=talent_uid)
    if data.meeting_type == MeetingType.GOOGLE_MEET:
        meeting_response = meeting.google_meet.create_meeting(data.meeting, data.meeting.google_meet_specifi.get("access_token"))
    elif data.meeting_type == MeetingType.ZOOM:
        meeting_response = meeting.zoom.create_meeting(data.meeting)
    elif data.meeting_type == MeetingType.MICROSOFT_TEAMS:
        meeting_response = meeting.teams.create_meeting(data.meeting)
    if not meeting_response:
        raise HttpError(400, "Meeting could not be scheduled")

    return meeting_response