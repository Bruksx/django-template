from uuid import UUID

from django.core.mail import send_mail
from django.db import transaction
from helpers.images import convert_base64_to_image_file
from ninja import Router, PatchDict
from ninja.errors import HttpError
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth

from accounts.enums import UserType, AuthType
from accounts.models import Talent, AdditionalSkill, TalentAvailableDay
from accounts.models import User, VerificationCode, Education, Experience
from accounts.schemas import common as common_schemas
from accounts.schemas import talent as talent_schemas


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
        data["photo"] = convert_base64_to_image_file(data["photo"])
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

@router.patch("talent-profile", response=talent_schemas.UserSchema, auth=JWTAuth())
def update_talent_profile(request, data: talent_schemas.UpdateTalentProfileSchema):
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

