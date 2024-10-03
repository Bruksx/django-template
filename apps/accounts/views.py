import logging
from datetime import date, timedelta
from typing import List
from uuid import UUID

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from helpers.images import convert_base64_to_image_file
from helpers.utils import convert_base64_to_file
from ninja import Router, PatchDict
from ninja.errors import HttpError
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth

from accounts.enums import UserType, AuthType
from accounts.models import Talent, AdditionalSkill, TalentAvailableDay, Country, EducationLevel, Role, CustomerCase
from accounts.models import User, VerificationCode, Education, Experience
from accounts.schemas import common as common_schemas
from accounts.schemas import talent as talent_schemas
from accounts.schemas.talent import CountrySchema, EducationLevelSchema, RoleSchema, TalentDashboardReport, \
    MonthlyChartSchema, MutateEducationSchema, MutateExperienceSchema, MutateTalentAvailableDaySchema, \
    TalentChangePasswordSchema
from chats.schemas import ResponseSchema

router = Router(tags=["Account"])

@router.post("create-account/")
def create_account(request, data: common_schemas.RegisterSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode(email=data.email)
    raw_code = verification_code.save()
    send_mail(
        "OTP",
        f"{raw_code}",
        "from@example.com",
        [data.email],
        fail_silently=False,
    )
    return {
        "message": "verification mail sent!"
    }


@router.post("validate-otp", response={200:talent_schemas.LoggedInUserSchema})
@transaction.atomic
def validate_otp(request, data: talent_schemas.ValidateTalentOTPSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode.objects.filter(email=data.email).last()
    if not verification_code:
        raise HttpError(400, "Incorrect otp")
    is_correct = verification_code.verify_code(data.otp)
    if not is_correct:
        raise HttpError(400, "This OTP is invalid")
    user = User.objects.create_user(first_name=data.first_name,
                                    last_name=data.last_name,
                                    email=data.email,
                                    password=data.password,
                                    username=None,
                                    phone_number=data.phone_number,
                                    auth_mode=AuthType.EMAIL.value,
                               type=UserType.TALENT.value,
                               email_verified=True, is_active=True)
    Talent.objects.create(
        user=user,
        country=data.country,
        preferred_communication=data.preferred_communication.value,
        state=data.state,
        city=data.city,
        postal_code=data.postal_code
    )
    return user



@router.patch("complete-profile/first_step",
             response=talent_schemas.UserSchema,
             auth=JWTAuth())
@transaction.atomic
def complete_talent_profile(request, data: PatchDict[talent_schemas.CompleteTalentProfileSchema]):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    if "gender" in data:
        talent_user.user.update(gender=data.pop("gender").value)
    availability = data.pop("availability", list())
    for available_day in availability:
        available_day["day"] = available_day["day"].value
        uid =  available_day.pop("uid", None)
        active = available_day.pop("active", True)
        if uid and not active:
            talent_user.talentavailableday_set.filter(uid=uid).delete()
        elif uid and active:
            talent_user.talentavailableday_set.filter(uid=uid).update(**available_day)
        elif not uid:
            day = available_day['day']
            if talent_user.talentavailableday_set.filter(day=day).exists():
                raise HttpError(400, f"{day} already exists")
            TalentAvailableDay.objects.create(**available_day, talent=talent_user)
    if data.get("photo"):
        data["photo"] = convert_base64_to_file(data["photo"])
    talent_user.update(**data)
    return talent_user.user


@router.patch("complete-profile/next_step", response=talent_schemas.UserSchema, auth=JWTAuth())
@transaction.atomic
def complete_talent_profile2(request, data: PatchDict[talent_schemas.CompleteTalentProfileSchema2]):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    education_history = data.pop("education_history", list())
    for education in education_history:
        edu_uid = education.pop("uid", None)
        if edu_uid:
            talent_user.education_set.filter(uid=edu_uid).update(**education)
        else:
            Education(**education, talent=talent_user).save()
    additional_languages = data.pop("additional_languages", list())
    if "cv" in data:
        data["cv"] = convert_base64_to_file(data["cv"])
    talent_user.update(**data)
    talent_user.additional_languages.set(additional_languages)
    return talent_user.user


@router.patch("complete-profile/last_step", response=talent_schemas.UserSchema, auth=JWTAuth())
@transaction.atomic
def complete_talent_profile3(request, data: PatchDict[talent_schemas.CompleteTalentProfileSchema3]):
    talent_user: Talent = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    if "skills" in data:
        talent_user.skills.set(data["skills"])
    if "business_models" in data:
        talent_user.business_models.set(data["business_models"])
    if "additional_skills" in data:
        talent_user.additionalskill_set.exclude(name__in=data["additional_skills"]).delete()
        existing_skills = talent_user.get_additional_skills()
        AdditionalSkill.objects.bulk_create(
            [
                AdditionalSkill(name=skill, talent=talent_user)
                for skill in data["additional_skills"]
                if skill not in existing_skills
            ]
        )
    if "experience_history" in data:
        for experience in data["experience_history"]:
            experience_uid = experience.pop("uid", None)
            if experience_uid:
                Experience.objects.filter(uid=experience_uid).update(**experience)
            else:
                Experience(**experience, talent=talent_user).save()
    return talent_user.user

@router.get("talent-profile", response=talent_schemas.TalentUserSchema, auth=JWTAuth())
def talent_profile(request):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    return talent_user

@router.get("talents", response=talent_schemas.TalentUserListSchema, auth=JWTAuth())
def talent_lists(request, search:str):
    talents = Talent.objects.prefetch_related("user").all()
    if search:
        talents = talents.filter(Q(user__first_name__icontains=search)|
                                 Q(user__last_name__icontains=search)|
                                 Q(user__email__icontains=search)
                                 )
    return talents


@router.post("talent-profile", response=talent_schemas.UserSchema, auth=JWTAuth())
def create_talent_profile(request, data: talent_schemas.UpdateTalentProfileSchema):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    talent_user.user.update(first_name=data.first_name,
                                    last_name=data.last_name,
                                    phone_number=data.phone_number)
    talent_user = talent_user.update(
        country=data.country,
        preferred_communication=data.preferred_communication.value,
        state=data.state,
        city=data.city,
        postal_code=data.postal_code
    )
    return talent_user.user

@router.delete("talent/education/{education_uid}",
               response={204: None},
               auth=JWTAuth())
def delete_talent_education(request, education_uid:UUID):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    education = talent_user.education_set.filter(uid=education_uid).first()
    if not education:
        raise HttpError(404, "This education does not exist")
    education.delete()
    return Response(status=204, data=None)


@router.delete("talent/experience/{experience_uid}",
               response={204: None}, auth=JWTAuth())
def delete_talent_experience(request, experience_uid:UUID):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    experience = talent_user.experience_set.filter(uid=experience_uid).first()
    if not experience:
        raise HttpError(404, "This experience does not exist")
    experience.delete()
    return Response(status=204, data=None)


@router.get("countries", response=List[CountrySchema], tags=["Common"], auth=JWTAuth())
def country_list(request):
    return Country.objects.all()


@router.get("educational-levels", response=List[EducationLevelSchema], auth=JWTAuth(),
            tags=["Common"])
def educational_levels(request):
    return EducationLevel.objects.all()


@router.get("talent/dashboard-report", response=TalentDashboardReport, auth=JWTAuth(),
            tags=["Talent Dashboard"])
def talent_dashboard_report(request, start_date: date=None, end_date: date=None):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only talents are allowed here")
    if start_date and end_date:
        # if the range is inclusive
        end_date = end_date + timedelta(days=1)
        return Response(data=TalentDashboardReport.from_orm(user.talent, context={
                "start_date": start_date,
                "end_date": end_date
            }))

    return Response(data=TalentDashboardReport.from_orm(user.talent))

@router.get("talent/applications-chart", response=List[MonthlyChartSchema], auth=JWTAuth(),
            tags=["Talent Dashboard"])
def talent_applications_chart(request):
    user = request.user
    if not hasattr(user, "talent", ):
        raise HttpError(403, "Only talents are allowed here")
    return user.talent.applications_made_chart()


@router.get("talent/interviews-chart", response=List[MonthlyChartSchema],
            tags=["Talent Dashboard"], auth=JWTAuth())
def talent_interview_chart(request):
    user = request.user
    if not hasattr(user, "talent", ):
        raise HttpError(403, "Only talents are allowed here")
    return user.talent.interviews_chart()


@router.patch("talent/profile", auth=JWTAuth())
def update_talent_profile(request, data: PatchDict[talent_schemas.UpdateTalentProfileSchema2]):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    if "gender" in data:
        data["gender"] = data["gender"].value
    if "preferred_communication" in data:
        data["preferred_communication"] = data["preferred_communication"].value
    user = request.user
    user_data = dict()
    if "first_name" in data:
        user_data["first_name"] = data.pop("first_name", None)
    if "last_name" in data:
        user_data["last_name"] = data.pop("last_name", None)
    if "gender" in data:
        user_data["gender"] = data.pop("gender", None)
    if "phone_number" in data:
        user_data["phone_number"] = data.pop("phone_number")
    user.update(**user_data)
    talent_user.update(**data)
    return Response(status=200, data={"message": "Profile updated successfully"})


@router.patch("talent/education-history", auth=JWTAuth())
def update_education_history(request, data: List[PatchDict[MutateEducationSchema]]):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    for education in data:
        edu_uid = education.pop("uid", None)
        if edu_uid:
            talent_user.education_set.filter(uid=edu_uid).update(**education)
        else:
            Education(**education, talent=talent_user).save()
    return Response(status=200, data={"message": "Education history updated successfully"})

@router.patch("talent/experience-history", auth=JWTAuth())
def update_experience_history(request, data:List[PatchDict[MutateExperienceSchema]]):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    for experience in data:
        experience_uid = experience.pop("uid", None)
        if experience_uid:
            Experience.objects.filter(uid=experience_uid).update(**experience)
        else:
            Experience(**experience, talent=talent_user).save()
    return Response(status=200, data={"message": "Experience history updated successfully"})

@router.patch("talent/availability", auth=JWTAuth())
def update_talent_availability(request, data: List[PatchDict[MutateTalentAvailableDaySchema]]):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    for available_day in data:
        available_day["day"] = available_day["day"].value
        uid =  available_day.pop("uid", None)
        active = available_day.pop("active", True)
        if uid and not active:
            talent_user.talentavailableday_set.filter(uid=uid).delete()
        elif uid and active:
            talent_user.talentavailableday_set.filter(uid=uid).update(**available_day)
        elif not uid:
            day = available_day['day']
            if talent_user.talentavailableday_set.filter(day=day).exists():
                raise HttpError(400, f"{day} already exists")
            TalentAvailableDay.objects.create(**available_day, talent=talent_user)
    return Response(status=200, data={"message": "Availability updated successfully"})

@router.patch("talent/change-password", auth=JWTAuth())
def change_talent_password(request, data: TalentChangePasswordSchema):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    user = request.user
    if not user.check_password(data.old_password):
        raise HttpError(400, "Incorrect Password")
    user.set_password(data.new_password)
    user.save()
    return Response(status=200, data={"message": "Password changed successfully"})

@router.post("customer-cases", auth=JWTAuth())
def create_customer_case(request, data: PatchDict[common_schemas.CreateCustomerCaseSchema]):
    user = request.user
    if user.customercase_set.filter(**data).exists():
        raise HttpError(400, "Case already exists")
    CustomerCase.objects.create(**data, user=user).save()
    return Response(status=200, data={"message": "Case created successfully"})




